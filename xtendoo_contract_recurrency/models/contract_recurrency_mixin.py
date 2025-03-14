from odoo import api, fields, models

class ContractRecurrencyMixinInherited(models.AbstractModel):
    _inherit = "contract.recurrency.mixin"

    last_date_invoiced = fields.Date(readonly=False, copy=False)
