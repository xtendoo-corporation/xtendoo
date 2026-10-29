from odoo.tests import tagged

from .common import XtdAiCase


@tagged("post_install", "-at_install")
class TestScreenContext(XtdAiCase):
    """What the user has on screen reaches the agent only if they can read it."""

    def screen(self, user, screen):
        return self.env["xtd.ai.conversation"].with_user(user)._xtd_ai_screen(screen)

    def test_record_on_screen_is_kept_with_its_name(self):
        partner = self.env["res.partner"].create({"name": "Cliente en Pantalla SL"})
        result = self.screen(
            self.user,
            {"model": "res.partner", "view_type": "form", "res_id": partner.id},
        )
        self.assertEqual(result["model"], "res.partner")
        self.assertEqual(result["res_id"], partner.id)
        self.assertEqual(result["name"], "Cliente en Pantalla SL")
        self.assertTrue(result["label"])

    def test_list_keeps_only_the_model(self):
        result = self.screen(self.user, {"model": "res.partner", "view_type": "list"})
        self.assertEqual(set(result), {"model", "label"})

    def test_unreadable_or_odd_screens_are_dropped(self):
        for bad in (
            None,
            "res.partner",
            {"model": "no.such.model"},
            {"model": "xtd.ai.audit"},
            {"model": "ir.config_parameter"},
            {"model": "res.users", "res_id": self.user.id},
            {"model": "base.language.install"},  # transient
            {"model": 42},
        ):
            self.assertFalse(self.screen(self.user, bad), bad)
        # a record that does not exist: only the model survives
        result = self.screen(self.user, {"model": "res.partner", "res_id": 999999999})
        self.assertNotIn("res_id", result)
        # a record hidden by the user's record rules (another company)
        hidden = self.env["res.partner"].create(
            {"name": "Socio Oculto", "company_id": self.company2.id}
        )
        self.user.company_ids = self.company
        result = self.screen(self.user, {"model": "res.partner", "res_id": hidden.id})
        self.assertNotIn("res_id", result)
        self.assertNotIn("name", result)

    def test_screen_note_reaches_the_history(self):
        partner = self.env["res.partner"].create({"name": "Proveedor [Visto]\nSL"})
        conversation = self.env["xtd.ai.conversation"].with_user(self.user)
        run, _token = conversation._xtd_ai_start_run(
            "¿qué me debe este?",
            screen={"model": "res.partner", "view_type": "form", "res_id": partner.id},
        )
        history = run.conversation_id.with_user(self.user)._xtd_ai_history_messages()
        text = history[-1]["text"]
        self.assertTrue(text.startswith("[Pantalla del usuario: "), text)
        self.assertIn(f"(modelo res.partner, id {partner.id})]", text)
        # the record name can never open or close the bracketed note
        self.assertIn("«Proveedor (Visto) SL»", text)
        self.assertTrue(text.endswith("¿qué me debe este?"))
