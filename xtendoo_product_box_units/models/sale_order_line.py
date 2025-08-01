# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    boxes = fields.Float(
        string='Boxes',
        digits='Product Unit of Measure',
        default=1.0,
        help='Number of boxes for this product'
    )
    box_units = fields.Float(
        string='Units per Box',
        help='Units per box from product configuration'
    )

    @api.onchange('boxes', 'product_id')
    def _onchange_boxes(self):
        """Calculate quantity based on boxes and box_units when boxes change"""
        if self.boxes and self.box_units:
            self.product_uom_qty = self.boxes * self.box_units

    @api.onchange('product_id')
    def _onchange_product_id_box_units(self):
        """Load box_units when product changes and recalculate if boxes is set"""
        if self.product_id and self.boxes:
            self.box_units = self.product_id.product_tmpl_id.box_units
            self.product_uom_qty = self.boxes * self.box_units

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty_boxes(self):
        """Update boxes when quantity is changed manually"""
        if self.product_uom_qty and self.box_units and self.box_units > 0:
            self.boxes = self.product_uom_qty / self.box_units

    def _prepare_invoice_line(self, **optional_values):
        """Override to pass boxes value to invoice line"""
        values = super()._prepare_invoice_line(**optional_values)
        values.update({
            'boxes': self.boxes,
        })
        return values
