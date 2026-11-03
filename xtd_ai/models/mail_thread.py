from odoo import models

from ..tools.errors import XtdAiDraftOnlyError
from ..tools.unlock import is_unlocked


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _xtd_ai_note_unlocked(self, kwargs):
        """The call is the internal note of a tool granted ``*.message_post``
        (log_note) on this one record (§6.5); emails and comments to followers
        stay blocked."""
        return (
            is_unlocked(self, "message_post")
            and kwargs.get("message_type") == "comment"
            and kwargs.get("subtype_xmlid") == "mail.mt_note"
            and not kwargs.get("partner_ids")
            and not kwargs.get("attachment_ids")
            and not kwargs.get("attachments")
        )

    def _xtd_ai_check_chatter(self, message_type):
        if self.env.context.get("xtd_ai_run") and message_type in ("comment", "email"):
            raise XtdAiDraftOnlyError(
                self.env._(
                    "El agente IA no puede escribir en el chatter ni enviar correos."
                )
            )

    def message_post(self, **kwargs):
        # send_email: the confirmed card of a tool that writes to the customer
        # (quotation, payment reminder) on this one record (§6.5)
        if not (is_unlocked(self, "send_email") or self._xtd_ai_note_unlocked(kwargs)):
            self._xtd_ai_check_chatter(kwargs.get("message_type", "notification"))
        return super().message_post(**kwargs)

    def message_notify(self, **kwargs):
        # message_notify sends emails to partners: not allowed to the agent either.
        if self.env.context.get("xtd_ai_run"):
            raise XtdAiDraftOnlyError(
                self.env._(
                    "El agente IA no puede escribir en el chatter ni enviar correos."
                )
            )
        return super().message_notify(**kwargs)
