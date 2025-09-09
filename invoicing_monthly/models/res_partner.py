
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    monthly_invoicing = fields.Boolean(string='Monthly Invoicing', default=False,
        help="It can only be billed monthly")