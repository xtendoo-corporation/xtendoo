# See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class StockPicking(models.Model):
    _inherit = "stock.picking"

    digital_signature = fields.Binary(string='Digital signature')
    # vat_receiver = fields.Char(
    #     'Vat receiver',
    #     help='This is the Vat receiver'
    # )
    # name_receiver = fields.Char(
    #     'Name receiver',
    #     help='This is the Name receiver'
    # )
