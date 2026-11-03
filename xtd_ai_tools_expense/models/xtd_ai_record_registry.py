from odoo import api, models

from odoo.addons.xtd_ai.tools.errors import XtdAiToolError


class XtdAiRecordRegistry(models.AbstractModel):
    _inherit = "xtd.ai.record.registry"

    @api.model
    def _xtd_ai_record_specs(self):
        specs = super()._xtd_ai_record_specs()
        specs["hr.expense"] = {
            "label": self.env._("gasto"),
            "skill": "gastos",
            "create": True,
            "update": True,
            # a receipt is text from outside and money of the company: the
            # creation is always a card, in every profile
            "create_class": "confirm",
            "undo_create": True,
            "attachment": True,
            "domain": "_xtd_ai_domain_own_draft_expenses",
            "check": "_xtd_ai_check_hr_expense",
            "effects": "_xtd_ai_effects_hr_expense",
            "fields": {
                "name": {
                    "label": self.env._("Descripción"),
                    "risk": "low",
                    "required": True,
                },
                "product_id": {
                    "label": self.env._("Categoría"),
                    "risk": "low",
                    "risk_update": "money",
                    "domain": [("can_be_expensed", "=", True)],
                },
                "total_amount_currency": {
                    "label": self.env._("Importe total"),
                    "risk": "money",
                    "required": True,
                },
                "date": {"label": self.env._("Fecha"), "risk": "low"},
                "description": {"label": self.env._("Notas"), "risk": "low"},
                "payment_mode": {
                    "label": self.env._("Pagado por"),
                    "risk": "money",
                },
                # whose expense it is, its taxes, accounts and workflow: never
                "employee_id": {"risk": "forbidden"},
                "tax_ids": {"risk": "forbidden"},
                "account_id": {"risk": "forbidden"},
                "currency_id": {"risk": "forbidden"},
                "approval_state": {"risk": "forbidden"},
                "manager_id": {"risk": "forbidden"},
                "vendor_id": {"risk": "forbidden"},
                "quantity": {"risk": "forbidden"},
            },
        }
        return specs

    @api.model
    def _xtd_ai_domain_own_draft_expenses(self, model):
        return [("employee_id.user_id", "=", self.env.uid), ("state", "=", "draft")]

    @api.model
    def _xtd_ai_check_hr_expense(self, expense, vals):
        amount = vals.get("total_amount_currency")
        if amount is not None and amount <= 0:
            raise XtdAiToolError(
                "validation", self.env._("El importe debe ser mayor que cero.")
            )
        if not expense and not self.env.user.employee_id:
            raise XtdAiToolError(
                "forbidden",
                self.env._(
                    "Tu usuario no tiene empleado asociado: pide a RR. HH. que lo "
                    "vinculen para poder registrar gastos."
                ),
            )

    @api.model
    def _xtd_ai_effects_hr_expense(self, expense, vals):
        if expense:
            return []
        return [
            self.env._(
                "Queda en borrador a tu nombre con el ticket adjunto; enviarlo a "
                "aprobar lo haces tú en XTD."
            )
        ]
