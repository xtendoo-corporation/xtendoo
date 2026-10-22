from odoo import api, models

from ..tools.errors import XtdAiDraftOnlyError


class MailMail(models.Model):
    _inherit = "mail.mail"

    @api.model_create_multi
    def create(self, vals_list):
        # Last line of defence: an AI run must never queue an outgoing email,
        # even through a flow that does not go through message_post.
        if self.env.context.get("xtd_ai_run"):
            raise XtdAiDraftOnlyError(
                self.env._(
                    "El agente IA no puede escribir en el chatter ni enviar correos."
                )
            )
        return super().create(vals_list)
