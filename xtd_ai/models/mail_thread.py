from odoo import models

from ..tools.errors import XtdAiDraftOnlyError


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _xtd_ai_check_chatter(self, message_type):
        if self.env.context.get("xtd_ai_run") and message_type in ("comment", "email"):
            raise XtdAiDraftOnlyError(
                self.env._(
                    "El agente IA no puede escribir en el chatter ni enviar correos."
                )
            )

    def message_post(self, **kwargs):
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
