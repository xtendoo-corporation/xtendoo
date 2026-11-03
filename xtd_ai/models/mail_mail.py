from odoo import api, models

from ..tools.errors import XtdAiDraftOnlyError
from ..tools.unlock import unlocked_record


class MailMail(models.Model):
    _inherit = "mail.mail"

    @api.model_create_multi
    def create(self, vals_list):
        # Last line of defence: an AI run must never queue an outgoing email,
        # even through a flow that does not go through message_post.
        if (
            vals_list
            and self.env.context.get("xtd_ai_run")
            and not self._xtd_ai_mail_unlocked(vals_list)
        ):
            raise XtdAiDraftOnlyError(
                self.env._(
                    "El agente IA no puede escribir en el chatter ni enviar correos."
                )
            )
        return super().create(vals_list)

    def _xtd_ai_mail_unlocked(self, vals_list):
        """Only the emails of the message a tool granted ``send_email`` posted
        on its one record (a confirmed card): every mail must belong to a
        message of that record."""
        target = unlocked_record(self.env, "send_email")
        if not target:
            return False
        # sudo: the guard reads the messages it is about to send, nothing else
        messages = self.env["mail.message"].sudo()
        for vals in vals_list:
            message = messages.browse(vals.get("mail_message_id") or 0).exists()
            if not message or (message.model, message.res_id) != target:
                return False
        return True
