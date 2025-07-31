# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    boxes = fields.Float(
        string='Boxes',
        digits='Product Unit of Measure',
        default=0.0,
        help='Number of boxes for this product'
    )
    box_units = fields.Float(
        string='Units per Box',
        related='product_id.product_tmpl_id.box_units',
        readonly=True,
        help='Units per box from product configuration'
    )

    @api.onchange('boxes', 'product_id')
    def _onchange_boxes(self):
        """Calculate quantity based on boxes and box_units when boxes change"""
        if self.boxes and self.box_units:
            self.quantity = self.boxes * self.box_units

    @api.onchange('product_id')
    def _onchange_product_id_box_units(self):
        """Load box_units when product changes and recalculate if boxes is set"""
        if self.product_id and self.boxes:
            self.quantity = self.boxes * self.box_units

    @api.onchange('quantity')
    def _onchange_quantity_boxes(self):
        """Update boxes when quantity is changed manually"""
        if self.quantity and self.box_units and self.box_units > 0:
            self.boxes = self.quantity / self.box_units
