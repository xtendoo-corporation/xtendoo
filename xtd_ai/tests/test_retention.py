from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from ..models.xtd_ai_audit import (
    DEFAULT_AUDIT_RETENTION_DAYS,
    DEFAULT_CONVERSATION_RETENTION_DAYS,
    MIN_AUDIT_RETENTION_DAYS,
    MIN_CONVERSATION_RETENTION_DAYS,
    redact_personal,
    retention_days,
)
from .common import XtdAiCase

CONV = "xtd.ai.conversation"
TABLES = (
    "xtd_ai_conversation",
    "xtd_ai_message",
    "xtd_ai_run",
    "xtd_ai_pending_action",
)


@tagged("post_install", "-at_install")
class TestRetention(XtdAiCase):
    def age(self, conversation, days, only=TABLES):
        """Envejece la conversación y todo lo que cuelga de ella."""
        self.env.flush_all()
        when = fields.Datetime.now() - timedelta(days=days)
        for table in only:
            column = "id" if table == "xtd_ai_conversation" else "conversation_id"
            self.env.cr.execute(
                f"UPDATE {table} SET create_date = %s, write_date = %s "  # noqa: S608
                f"WHERE {column} = %s",
                (when, when, conversation.id),
            )
        self.env.invalidate_all()

    def make_conversation(self, user=None, finish=True):
        run, _token = self.start_run(user or self.user)
        if finish:
            run._xtd_ai_finish("done")
        return run.conversation_id, run

    def test_defaults_and_minimums(self):
        self.assertEqual(DEFAULT_CONVERSATION_RETENTION_DAYS, 90)
        self.assertEqual(DEFAULT_AUDIT_RETENTION_DAYS, 180)
        params = self.env["ir.config_parameter"].sudo()
        key = "xtd_ai.audit_retention_days"
        params.set_param(key, "1")
        self.assertEqual(
            retention_days(self.env, key, 180, MIN_AUDIT_RETENTION_DAYS),
            MIN_AUDIT_RETENTION_DAYS,
        )
        for bad in ("abc", "0", "-5", ""):
            params.set_param(key, bad)
            self.assertEqual(retention_days(self.env, key, 180, 30), 180)
        params.set_param(key, "45")
        self.assertEqual(retention_days(self.env, key, 180, 30), 45)

    def test_purges_conversation_without_activity(self):
        conversation, _run = self.make_conversation()
        self.age(conversation, DEFAULT_CONVERSATION_RETENTION_DAYS + 10)
        self.env[CONV]._xtd_ai_cron_retention()
        self.assertFalse(conversation.exists())

    def test_old_write_date_but_recent_message_is_kept(self):
        """Riesgo 7: el write_date de la conversación no cambia con cada mensaje."""
        conversation, _run = self.make_conversation()
        self.age(conversation, 400, only=("xtd_ai_conversation",))
        self.env[CONV]._xtd_ai_cron_retention()
        self.assertTrue(conversation.exists())

    def test_recent_run_keeps_old_conversation(self):
        conversation, run = self.make_conversation()
        self.age(conversation, 400)
        self.env.cr.execute(
            "UPDATE xtd_ai_run SET write_date = now() WHERE id = %s", [run.id]
        )
        self.env.invalidate_all()
        self.env[CONV]._xtd_ai_cron_retention()
        self.assertTrue(conversation.exists())

    def test_run_in_progress_is_never_purged(self):
        for state in ("queued", "running"):
            conversation, run = self.make_conversation(finish=False)
            run.state = state
            self.age(conversation, 400)
            self.env[CONV]._xtd_ai_cron_retention()
            self.assertTrue(conversation.exists(), state)

    def test_pending_card_is_never_purged(self):
        conversation, run = self.make_conversation()
        action = self.env["xtd.ai.pending_action"].sudo().create(
            {
                "run_id": run.id,
                "conversation_id": conversation.id,
                "user_id": self.user.id,
                "tool_name": "create_contact",
                "arguments": {"name": "X"},
                "cids": [self.company.id],
            }
        )
        self.age(conversation, 400)
        self.env[CONV]._xtd_ai_cron_retention()
        self.assertTrue(conversation.exists())
        action.state = "cancelled"
        self.age(conversation, 400)
        self.env[CONV]._xtd_ai_cron_retention()
        self.assertFalse(conversation.exists())

    def test_audit_purge_batches(self):
        from ..models import xtd_ai_audit as audit_module

        Audit = self.env["xtd.ai.audit"]
        rows = Audit.browse()
        for i in range(5):
            rows |= Audit._xtd_ai_log("tool_call", "ok", tool_name=f"old_{i}")
        keep = Audit._xtd_ai_log("tool_call", "ok", tool_name="fresh")
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE xtd_ai_audit SET create_date = %s WHERE id IN %s",
            (fields.Datetime.now() - timedelta(days=400), tuple(rows.ids)),
        )
        Audit.invalidate_model()
        old_batch, audit_module.PURGE_BATCH = audit_module.PURGE_BATCH, 2
        try:
            Audit._xtd_ai_cron_purge()
        finally:
            audit_module.PURGE_BATCH = old_batch
        self.assertFalse(rows.exists())
        self.assertTrue(keep.exists())

    def test_audit_respects_minimum(self):
        Audit = self.env["xtd.ai.audit"]
        row = Audit._xtd_ai_log("tool_call", "ok", tool_name="t")
        self.env["ir.config_parameter"].sudo().set_param(
            "xtd_ai.audit_retention_days", "1"
        )
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE xtd_ai_audit SET create_date = %s WHERE id = %s",
            (fields.Datetime.now() - timedelta(days=MIN_AUDIT_RETENTION_DAYS - 5), row.id),
        )
        Audit.invalidate_model()
        Audit._xtd_ai_cron_purge()
        self.assertTrue(row.exists())

    def test_conversation_minimum(self):
        conversation, _run = self.make_conversation()
        self.env["ir.config_parameter"].sudo().set_param(
            "xtd_ai.conversation_retention_days", "1"
        )
        self.age(conversation, MIN_CONVERSATION_RETENTION_DAYS - 5)
        self.env[CONV]._xtd_ai_cron_retention()
        self.assertTrue(conversation.exists())

    # -- minimización ------------------------------------------------------
    def test_redaction_of_personal_data(self):
        args = {
            "name": "Construcciones Garcia SL",
            "vat": "B12345678",
            "email": "juan.perez@example.com",
            "phone": "612 345 678",
            "iban": "ES9121000418450200051332",
            "partner_id": 42,
            "note": (
                "Llamar a +34 612345678 o a ana@empresa.es; cuenta "
                "ES91 2100 0418 4502 0005 1332, NIF 12345678Z, "
                "CIF A1234567B, NIE X1234567L."
            ),
            "lines": [{"email": "otro@x.org", "qty": 3}],
        }
        out = redact_personal(args)
        self.assertEqual(out["partner_id"], 42)
        self.assertEqual(out["lines"][0]["qty"], 3)
        self.assertEqual(out["name"], "Construcciones Garcia SL")
        blob = str(out)
        for secret in (
            "B12345678",
            "juan.perez",
            "612 345 678",
            "612345678",
            "ES9121000418450200051332",
            "2100 0418",
            "ana@empresa",
            "12345678Z",
            "A1234567B",
            "X1234567L",
            "otro@x.org",
        ):
            self.assertNotIn(secret, blob)
        self.assertIn("***", blob)

    def test_audit_log_stores_redacted_arguments(self):
        row = self.env["xtd.ai.audit"]._xtd_ai_log(
            "tool_call",
            "ok",
            tool_name="create_contact",
            arguments={"name": "Acme", "email": "jefe@acme.com", "vat": "ESB12345678"},
            record_refs=[{"model": "res.partner", "id": 7}],
        )
        self.assertNotIn("jefe@acme.com", str(row.arguments))
        self.assertNotIn("B12345678", str(row.arguments))
        self.assertEqual(row.arguments["name"], "Acme")
        self.assertEqual(row.record_refs, [{"model": "res.partner", "id": 7}])
