from odoo import models

from ..tools.errors import XtdAiDraftOnlyError

# Context key set ONLY by the log_note tool around its own message_post: it
# lifts the chatter guard for one internal note on one record (§6.5 "unlock
# per tool"); emails and comments to followers stay blocked.
NOTE_UNLOCK_KEY = "xtd_ai_unlock_note"


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _xtd_ai_note_unlocked(self, kwargs):
        """The call is the internal note the log_note tool is posting."""
        unlock = self.env.context.get(NOTE_UNLOCK_KEY)
        return (
            len(self) == 1
            and unlock == f"{self._name},{self.id}"
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
        if not self._xtd_ai_note_unlocked(kwargs):
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
