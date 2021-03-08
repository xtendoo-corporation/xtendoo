# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "mail.thread"]

    digital_signature = fields.Binary(string="Digital Signature", attachment=True)
    vat_receiver = fields.Char("Vat receiver", help="This is the Vat receiver",)
    name_receiver = fields.Char("Name receiver", help="This is the Name receiver",)
