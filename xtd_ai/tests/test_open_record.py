from odoo.tests import tagged

from .common import XtdAiCase


@tagged("post_install", "-at_install")
class TestOpenRecord(XtdAiCase):
    def setUp(self):
        super().setUp()
        self.run, _token = self.start_run(self.user)

    def open(self, args, user=None):
        return self.call(user or self.user, self.run, "open_record", args)[
            "structuredContent"
        ]

    def test_opens_a_readable_record_on_screen(self):
        partner = self.env["res.partner"].create({"name": "Abrir SL"})
        structured = self.open({"model": "res.partner", "id": partner.id})
        self.assertEqual(structured["status"], "ok", structured)
        ref = structured["records"][0]
        self.assertEqual(
            (ref["model"], ref["id"], ref["name"], ref["navigate"]),
            ("res.partner", partner.id, "Abrir SL", True),
        )
        # the run keeps it, so the chat opens it when the answer ends
        self.assertTrue(any(r.get("navigate") for r in self.run.record_refs))

    def test_models_outside_the_whitelist_are_refused(self):
        for model in ("res.users", "ir.config_parameter", "xtd.ai.audit", "foo.bar"):
            structured = self.open({"model": model, "id": 1})
            self.assertEqual(structured["error"]["code"], "validation", model)

    def test_missing_records_are_not_found(self):
        structured = self.open({"model": "res.partner", "id": 999999999})
        self.assertEqual(structured["error"]["code"], "not_found")

    def test_it_is_a_read_tool_without_confirmation(self):
        tool = self.env["xtd.ai.toolbox"]._xtd_ai_tools()["open_record"]
        self.assertEqual(tool["kind"], "read")

    def test_opening_a_record_already_read_still_navigates(self):
        partner = self.env["res.partner"].create({"name": "Leído y abierto SL"})
        self.call(self.user, self.run, "search_partners", {"query": "Leído y abierto"})
        self.open({"model": "res.partner", "id": partner.id})
        refs = [r for r in self.run.record_refs if r["id"] == partner.id]
        self.assertEqual(len(refs), 1)
        self.assertTrue(refs[0].get("navigate"))
