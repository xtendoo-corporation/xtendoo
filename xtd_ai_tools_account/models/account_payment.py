from odoo import api, models

from odoo.addons.xtd_ai_gateway.tools.errors import XtdAiDraftOnlyError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("xtd_ai_run"):
            raise XtdAiDraftOnlyError(self.env._("El agente IA no puede crear pagos."))
        return super().create(vals_list)

    def action_post(self):
        if self.env.context.get("xtd_ai_run"):
            raise XtdAiDraftOnlyError(
                self.env._("El agente IA no puede contabilizar pagos.")
            )
        return super().action_post()
