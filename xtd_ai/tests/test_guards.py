from odoo.exceptions import UserError
from odoo.tests import tagged

from ..tools.errors import XtdAiDraftOnlyError
from .common import XtdAiCase


@tagged("post_install", "-at_install")
class TestGuards(XtdAiCase):
    def setUp(self):
        super().setUp()
        self.run, _token = self.start_run()
        self.partner = self.env["res.partner"].create(
            {"name": "Guarded SL", "vat": "ESB12345678", "email": "g@example.com"}
        )
        self.agent_env = self.tool_env(self.user, self.run)
        # the user needs write rights on partners to prove the guard (not the ACL)
        # blocks
        self.agent_partner = self.agent_env["res.partner"].browse(self.partner.id)

    def test_partner_unlink_blocked_only_in_run(self):
        with self.assertRaises(XtdAiDraftOnlyError):
            self.agent_partner.unlink()
        self.assertTrue(self.partner.exists())
        other = self.env["res.partner"].create({"name": "Deletable"})
        other.with_user(self.user).unlink()  # no xtd_ai_run: normal behaviour
        self.assertFalse(other.exists())

    def test_partner_protected_write_blocked_only_in_run(self):
        for field, value in (
            ("name", "Renamed"),
            ("vat", "ESB99999999"),
            ("email", "x@example.com"),
            ("phone", "600"),
            ("street", "Calle 1"),
            ("active", False),
        ):
            with self.assertRaises(XtdAiDraftOnlyError, msg=field):
                self.agent_partner.write({field: value})
        self.assertEqual(self.partner.name, "Guarded SL")
        self.assertTrue(self.partner.active)
        self.partner.with_user(self.user).write({"name": "Renamed ok"})
        self.assertEqual(self.partner.name, "Renamed ok")

    def test_partner_unprotected_write_and_create_allowed(self):
        self.agent_partner.write({"comment": "note"})  # not protected
        self.assertIn("note", self.partner.comment)
        child = self.agent_env["res.partner"].create(
            {"name": "Child", "parent_id": self.partner.id}
        )
        self.assertEqual(child.parent_id, self.partner)
        self.assertEqual(child.vat, self.partner.vat)  # commercial sync still works
        self.assertEqual(child.env.context.get("_xtd_ai_partner_create"), None)
        with self.assertRaises(XtdAiDraftOnlyError):
            child.write({"name": "Renamed child"})

    def test_message_post_comment_blocked_in_run(self):
        record = self.agent_partner
        for message_type in ("comment", "email"):
            with self.assertRaises(XtdAiDraftOnlyError):
                record.message_post(body="hi", message_type=message_type)
        with self.assertRaises(XtdAiDraftOnlyError):
            record.message_notify(body="hi", partner_ids=self.user.partner_id.ids)
        # automatic tracking style notifications are allowed
        message = record.message_post(body="tracking", message_type="notification")
        self.assertTrue(message)
        # outside an AI run everything works
        self.partner.with_user(self.user).message_post(
            body="hi", message_type="comment"
        )

    def test_mail_mail_creation_blocked_in_run(self):
        vals = {"subject": "x", "body_html": "<p>x</p>", "email_to": "x@example.com"}
        with self.assertRaises(XtdAiDraftOnlyError):
            self.env["mail.mail"].with_context(xtd_ai_run=self.run.id).create(vals)
        self.assertTrue(self.env["mail.mail"].create(vals))  # outside an AI run

    def test_guard_error_mapped_and_audited(self):
        result = self.call(
            self.user, self.run, "zz_test_guard", {"partner_id": self.partner.id}
        )
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["error"]["code"], "draft_only")
        self.assertTrue(self.partner.exists())
        audit = self.audits(self.run)
        self.assertEqual(audit.mapped("event"), ["guard_blocked"])
        self.assertEqual(audit.mapped("outcome"), ["denied"])
        self.assertEqual(audit.mapped("error_code"), ["draft_only"])
        self.assertEqual(audit.mapped("tool_name"), ["zz_test_guard"])

    def test_draft_only_error_is_user_error(self):
        self.assertTrue(issubclass(XtdAiDraftOnlyError, UserError))
        self.assertEqual(XtdAiDraftOnlyError.code, "draft_only")

    def test_context_flags_for_silent_creation(self):
        result = self.call(self.user, self.run, "zz_test_env")
        self.assertTrue(result["structuredContent"]["data"]["xtd_ai_run"])
        context = self.agent_env.context
        self.assertTrue(context["mail_auto_subscribe_no_notify"])
        self.assertIs(context["mail_notify_force_send"], False)
