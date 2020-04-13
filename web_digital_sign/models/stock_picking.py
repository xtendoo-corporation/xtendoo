# See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class PickingType(models.Model):
    _inherit = 'stock.picking'

    digital_signature = fields.Binary(string='Digital signature')
