# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class ResPartner(models.Model):
    _inherit = "res.partner"

    client_discount = fields.Float(
        digits=dp.get_precision('Discount'),
        string='Descuento (%)'
    )

    discount_dpp = fields.Float(
        digits=dp.get_precision('Discount'),
        string='Descuento PP (%)'
    )
