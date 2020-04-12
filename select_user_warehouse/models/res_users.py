
from odoo import api, fields, models, _


class Users(models.Model):
    _inherit = "res.users"

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')












