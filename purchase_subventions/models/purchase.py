from odoo import _, api, fields, models

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    subvention_id = fields.Many2one(
        comodel_name="account.analytic.group",
    )
