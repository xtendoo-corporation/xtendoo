from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged

from .common import XtdAiCase


@tagged("post_install", "-at_install")
class TestUndo(XtdAiCase):
    """``xtd.ai.undo``: only intact drafts the user created, with their rights."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_group = cls.env.ref("base.group_partner_manager")

    def partner(self, **vals):
        return (
            self.env["res.partner"]
            .with_user(self.user)
            .create({"name": "Deshacer SL"} | vals)
        )

    def undo(self, record, user=None, **kw):
        user = user or self.user
        return (
            self.env["xtd.ai.undo"]
            .with_user(user)
            ._xtd_ai_undo(record._name, record.id, **kw)
        )

    def reason(self, record, user=None, **kw):
        user = user or self.user
        return (
            self.env["xtd.ai.undo"]
            .with_user(user)
            ._xtd_ai_undo_reason(record.with_user(user), **kw)
        )

    def test_undo_deletes_an_intact_contact_and_audits_it(self):
        partner = self.partner()
        self.assertEqual(
            self.env["xtd.ai.undo"]
            .with_user(self.user)
            ._xtd_ai_undo_state("res.partner", partner.id),
            "available",
        )
        result = self.undo(partner)
        self.assertEqual(result, {"undone": True, "mode": "unlink"})
        self.assertFalse(partner.exists())
        audit = self.env["xtd.ai.audit"].sudo().search([("event", "=", "undo")])
        self.assertEqual((audit.outcome, audit.user_id), ("ok", self.user))
        self.assertEqual(audit.record_refs[0]["id"], partner.id)
        self.assertEqual(
            self.env["xtd.ai.undo"]
            .with_user(self.user)
            ._xtd_ai_undo_state("res.partner", partner.id),
            "undone",
        )

    def test_a_contact_used_by_others_is_not_undoable(self):
        partner = self.partner()
        self.env["res.partner"].with_user(self.user).create(
            {"name": "Persona", "parent_id": partner.id}
        )
        self.assertIn("usan", self.reason(partner))
        result = self.undo(partner)
        self.assertFalse(result["undone"])
        self.assertTrue(partner.exists())
        audit = self.env["xtd.ai.audit"].sudo().search([("event", "=", "undo")])
        self.assertEqual((audit.outcome, audit.error_code), ("denied", "not_undoable"))

    def test_modified_by_someone_else_is_not_undoable(self):
        partner = self.partner()
        partner.with_user(self.env.ref("base.user_admin")).write({"comment": "tocado"})
        self.assertIn("modificado", self.reason(partner))
        self.assertFalse(self.undo(partner)["undone"])
        self.assertTrue(partner.exists())

    def test_only_the_creator_can_undo(self):
        partner = self.partner()
        other = self.user2
        other.sudo().group_ids = [(4, self.partner_group.id)]
        self.assertIn("modificado", self.reason(partner, user=other))
        self.assertTrue(partner.exists())

    def test_too_old_is_not_undoable(self):
        partner = self.partner()
        old = fields.Datetime.now() - timedelta(hours=5)
        self.env.cr.execute(
            "UPDATE res_partner SET create_date=%s WHERE id=%s", (old, partner.id)
        )
        partner.invalidate_recordset()
        self.assertIn("tiempo", self.reason(partner))
        self.env["ir.config_parameter"].sudo().set_param(
            "xtd_ai.undo_window_minutes", "600"
        )
        self.assertIsNone(self.reason(partner))

    def test_record_created_before_the_run_is_not_undone(self):
        partner = self.partner()
        since = partner.create_date + timedelta(seconds=5)
        self.assertIn("no lo ha creado", self.reason(partner, since=since).lower())
        self.assertFalse(self.undo(partner, since=since)["undone"])
        self.assertTrue(partner.exists())

    def test_models_outside_the_list_and_agent_context_are_refused(self):
        user_record = self.env["res.users"].browse(self.user.id)
        self.assertIn(
            "no se puede deshacer",
            self.env["xtd.ai.undo"]
            .with_user(self.user)
            ._xtd_ai_undo_reason(user_record)
            .lower(),
        )
        partner = self.partner()
        run, _token = self.start_run(self.user)
        env = self.tool_env(self.user, run)
        reason = env["xtd.ai.undo"]._xtd_ai_undo_reason(partner.with_env(env))
        self.assertIn("agente", reason)
        self.assertTrue(partner.exists())

    def test_without_unlink_right_the_contact_is_archived(self):
        partner = self.partner()
        undo = self.env["xtd.ai.undo"].with_user(self.user)
        # Contacts of the user: no delete right, but writing is (own contact rule)
        with patch.object(type(undo), "_xtd_ai_undo_mode", return_value="archive"):
            result = undo._xtd_ai_undo("res.partner", partner.id)
        self.assertTrue(result["undone"], result)
        self.assertEqual(result["mode"], "archive")
        self.assertFalse(partner.active)
        self.assertEqual(undo._xtd_ai_undo_state("res.partner", partner.id), "undone")
