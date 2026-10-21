import base64
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import XtdAiCase, make_pdf, make_png

CONV = "xtd.ai.conversation"


@tagged("post_install", "-at_install")
class TestAttachments(XtdAiCase):
    def conversation(self, user=None):
        return self.env[CONV].with_user(user or self.user)._xtd_ai_open()

    def messages(self, conversation):
        return (
            self.env["xtd.ai.message"]
            .sudo()
            .search([("conversation_id", "=", conversation.id)])
        )

    # -- start_run -------------------------------------------------------
    def test_attachment_only_message(self):
        pdf, png = self.upload(), self.upload(raw=make_png(), name="foto.png")
        run, _token = self.start_run(text="", attachment_ids=[pdf.id, png.id])
        message = self.messages(run.conversation_id)
        self.assertEqual(message.role, "user")
        self.assertEqual(message.body, "")
        self.assertEqual(message.attachment_ids, pdf | png)
        self.assertEqual(run.conversation_id.name, "factura.pdf")

    def test_empty_message_without_attachments_fails(self):
        with self.assertRaises(UserError):
            self.start_run(text="  ", attachment_ids=[])

    def test_history_lists_attachments_without_content(self):
        pdf = self.upload()
        run, _token = self.start_run(text="mira", attachment_ids=[pdf.id])
        status, response = self.rpc(self.user, run, "xtd_ai/history")
        self.assertEqual(status, 200)
        history = response["result"]
        self.assertEqual(
            history["messages"][-1]["attachments"],
            [
                {
                    "id": pdf.id,
                    "name": "factura.pdf",
                    "mimetype": "application/pdf",
                    "size": pdf.file_size,
                }
            ],
        )
        self.assertTrue(history["confirm_writes"])
        self.assertNotIn("data", str(history["messages"][-1]["attachments"]))

    def assert_rejected(self, attachment_ids, user=None):
        before = self.env["xtd.ai.message"].sudo().search_count([])
        runs = self.env["xtd.ai.run"].sudo().search_count([])
        with self.assertRaises(UserError):
            self.start_run(user, attachment_ids=attachment_ids)
        self.assertEqual(self.env["xtd.ai.message"].sudo().search_count([]), before)
        self.assertEqual(self.env["xtd.ai.run"].sudo().search_count([]), runs)

    def test_other_users_attachment(self):
        mine = self.upload(self.user)
        self.upload(self.user2)
        self.assert_rejected([mine.id], user=self.user2)
        # an attachment on my conversation created by someone else
        conversation = self.conversation(self.user)
        other = (
            self.env["ir.attachment"]
            .sudo()
            .create(
                {
                    "name": "x.pdf",
                    "raw": make_pdf(),
                    "res_model": CONV,
                    "res_id": conversation.id,
                }
            )
        )
        self.env.cr.execute(
            "UPDATE ir_attachment SET create_uid = %s WHERE id = %s",
            [self.user2.id, other.id],
        )
        other.invalidate_recordset()
        self.assert_rejected([other.id], user=self.user)

    def test_other_conversation_attachment(self):
        old = self.conversation()
        att = self.upload(conversation=old)
        old.with_user(self.user).action_close()
        self.assertTrue(self.conversation() != old)
        self.assert_rejected([att.id])

    def test_foreign_model_and_missing_ids(self):
        partner_att = (
            self.env["ir.attachment"]
            .with_user(self.user)
            .create(
                {
                    "name": "p.pdf",
                    "raw": make_pdf(),
                    "res_model": "res.partner",
                    "res_id": self.user.partner_id.id,
                }
            )
        )
        self.assert_rejected([partner_att.id])
        self.assert_rejected([987654321])
        self.assert_rejected(["1"])
        self.assert_rejected([True])

    def test_wrong_type(self):
        text = self.upload(raw=b"just some text", name="notas.txt")
        self.assert_rejected([text.id])
        fake = self.upload(raw=b"<html><script>1</script></html>", name="fake.pdf")
        self.assert_rejected([fake.id])
        empty = self.upload(raw=b"", name="vacio.pdf")
        self.assert_rejected([empty.id])

    def test_corrupt_pdf(self):
        broken = self.upload(raw=b"%PDF-1.4\nthis is not a pdf at all", name="rota.pdf")
        self.assert_rejected([broken.id])

    def test_too_big(self):
        att = self.upload()
        limits = (len(att.raw) - 1, 5, 20)
        with patch.object(
            type(self.env[CONV]), "_xtd_ai_attachment_limits", return_value=limits
        ):
            self.assert_rejected([att.id])

    def test_too_many_files_uses_parameter(self):
        atts = [self.upload(name=f"f{i}.pdf") for i in range(3)]
        self.env["ir.config_parameter"].sudo().set_param(
            "xtd_ai_gateway.attachment_max_files", "2"
        )
        self.assert_rejected([a.id for a in atts])
        run, _token = self.start_run(attachment_ids=[a.id for a in atts[:2]])
        self.assertTrue(run)

    def test_default_limits(self):
        self.assertEqual(
            self.env[CONV]._xtd_ai_attachment_limits(), (10 * 1024 * 1024, 5, 20)
        )

    def test_too_many_pdf_pages_uses_parameter(self):
        long_pdf = self.upload(raw=make_pdf(3), name="largo.pdf")
        self.env["ir.config_parameter"].sudo().set_param(
            "xtd_ai_gateway.attachment_max_pdf_pages", "2"
        )
        self.assert_rejected([long_pdf.id])
        short = self.upload(raw=make_pdf(2), name="corto.pdf")
        self.assertTrue(self.start_run(attachment_ids=[short.id]))

    def test_closed_conversation(self):
        conversation = self.conversation()
        att = self.upload(conversation=conversation)
        conversation.action_close()
        with self.assertRaises(UserError):
            conversation._xtd_ai_start_run("hola", attachment_ids=[att.id])

    def test_attachment_linked_to_another_message(self):
        att = self.upload()
        run, _token = self.start_run(attachment_ids=[att.id])
        run._xtd_ai_finish("done")
        self.assert_rejected([att.id])

    # -- xtd_ai/attachment -----------------------------------------------
    def fetch(self, user, run, att_id):
        return self.rpc(user, run, "xtd_ai/attachment", {"id": att_id})

    def test_mcp_attachment_ok_and_audited_without_content(self):
        raw = make_pdf()
        att = self.upload(raw=raw)
        run, _token = self.start_run(attachment_ids=[att.id])
        status, response = self.fetch(self.user, run, att.id)
        self.assertEqual(status, 200, response)
        result = response["result"]
        self.assertEqual(
            (result["id"], result["name"], result["mimetype"]),
            (att.id, "factura.pdf", "application/pdf"),
        )
        self.assertEqual(base64.b64decode(result["data_base64"]), raw)
        audit = self.audits(run, event="attachment_read")
        self.assertEqual(audit.mapped("outcome"), ["ok"])
        self.assertEqual(audit.arguments, {"id": att.id})
        self.assertNotIn(result["data_base64"][:40], str(audit.read()))

    def test_mcp_attachment_access_matrix(self):
        mine = self.upload(self.user)
        theirs = self.upload(self.user2)
        unlinked = self.upload(self.user, name="suelto.pdf")
        run, _token = self.start_run(attachment_ids=[mine.id])
        run2, _t = self.start_run(self.user2, attachment_ids=[theirs.id])
        # another user's attachment, an unlinked one and a missing one
        for att_id in (theirs.id, unlinked.id, 987654321):
            status, response = self.fetch(self.user, run, att_id)
            self.assertEqual((status, response["error"]["code"]), (403, -32003))
        # my attachment with the other user's run
        status, response = self.fetch(self.user2, run2, mine.id)
        self.assertEqual((status, response["error"]["code"]), (403, -32003))
        denied = self.audits(run, event="attachment_read").mapped("outcome")
        self.assertEqual(denied, ["denied"] * 3)
        for bad in ("1", None, True, 1.5):
            status, response = self.fetch(self.user, run, bad)
            self.assertEqual(response["error"]["code"], -32602)

    def test_mcp_attachment_needs_read_access(self):
        att = self.upload()
        run, _token = self.start_run(attachment_ids=[att.id])
        with patch.object(
            type(self.env["ir.attachment"]),
            "check_access",
            side_effect=AccessError("no"),
        ):
            status, response = self.fetch(self.user, run, att.id)
        self.assertEqual((status, response["error"]["code"]), (403, -32003))

    def test_mcp_attachment_size_guard(self):
        att = self.upload()
        run, _token = self.start_run(attachment_ids=[att.id])
        limits = (len(att.raw) - 1, 5, 20)
        with patch.object(
            type(self.env[CONV]), "_xtd_ai_attachment_limits", return_value=limits
        ):
            status, response = self.fetch(self.user, run, att.id)
        self.assertEqual(response["error"]["code"], -32602)

    # -- forced confirmation ---------------------------------------------
    def test_attachments_force_confirmation(self):
        self.set_confirm(self.user, False)
        att = self.upload()
        run, _token = self.start_run(attachment_ids=[att.id])
        result = self.call(self.user, run, "zz_test_draft", {"name": "tag-att"})
        self.assertEqual(
            result["structuredContent"]["status"], "pending_confirmation", result
        )
        self.assertFalse(
            self.env["res.partner.category"].sudo().search([("name", "=", "tag-att")])
        )
        status, response = self.rpc(self.user, run, "xtd_ai/history")
        self.assertTrue(response["result"]["confirm_writes"])

    def test_no_attachments_keep_user_preference(self):
        self.set_confirm(self.user, False)
        run, _token = self.start_run()
        result = self.call(self.user, run, "zz_test_draft", {"name": "tag-noatt"})
        self.assertEqual(result["structuredContent"]["status"], "ok")
        status, response = self.rpc(self.user, run, "xtd_ai/history")
        self.assertFalse(response["result"]["confirm_writes"])

    def test_next_message_without_attachments_is_not_forced(self):
        self.set_confirm(self.user, False)
        att = self.upload()
        run, _token = self.start_run(attachment_ids=[att.id])
        run._xtd_ai_finish("done")
        run2, _t = self.start_run(text="otra cosa")
        result = self.call(self.user, run2, "zz_test_draft", {"name": "tag-next"})
        self.assertEqual(result["structuredContent"]["status"], "ok")

    # -- helper for tools and retention ----------------------------------
    def test_toolbox_helper(self):
        att = self.upload()
        other = self.upload()
        run, _token = self.start_run(attachment_ids=[att.id])
        env = self.tool_env(self.user, run)
        toolbox = env["xtd.ai.toolbox"]
        self.assertEqual(toolbox._xtd_ai_conversation_attachment(att.id), att)
        from odoo.addons.xtd_ai_gateway.tools.errors import XtdAiToolError

        for bad in (other.id, 987654321, True):
            with self.assertRaises(XtdAiToolError):
                toolbox._xtd_ai_conversation_attachment(bad)

    def test_retention_removes_conversation_and_attachments(self):
        att = self.upload()
        conversation = self.conversation()
        run, _token = self.start_run(attachment_ids=[att.id])
        run._xtd_ai_finish("done")
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE xtd_ai_conversation SET write_date = now() - interval '400 days'"
            " WHERE id = %s",
            [conversation.id],
        )
        conversation.invalidate_recordset()
        self.env[CONV]._xtd_ai_cron_retention()
        self.assertFalse(conversation.exists())
        self.assertFalse(att.exists())
