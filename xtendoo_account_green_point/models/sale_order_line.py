from odoo import models, fields, api, _

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    green_point_applicable = fields.Boolean(related='product_id.green_point_enabled', store=True)
    green_point_amount_unit = fields.Float(string="Importe PV (Unidad)", compute="_compute_green_point", store=True, readonly=False, digits='Product Price')
    green_point_amount_line = fields.Float(string="Importe PV (Línea)", compute="_compute_green_point", store=True, readonly=False)
    price_subtotal_with_green_point = fields.Monetary(string="Subtotal + PV", compute="_compute_price_subtotal_gp")

    @api.depends('price_subtotal', 'green_point_amount_line')
    def _compute_price_subtotal_gp(self):
        for line in self:
            line.price_subtotal_with_green_point = line.price_subtotal + line.green_point_amount_line

    @api.depends('product_id', 'product_uom_qty')
    def _compute_green_point(self):
        for line in self:
            if not line.product_id or not line.product_id.green_point_enabled or line.display_type not in ('product', False, ''):
                line.green_point_amount_unit = 0.0
                line.green_point_amount_line = 0.0
                continue
            
            gpt = line.product_id.green_point_type
            if gpt == 'unit':
                line.green_point_amount_unit = line.product_id.green_point_amount
                line.green_point_amount_line = line.product_id.green_point_amount * line.product_uom_qty
            elif gpt == 'line':
                line.green_point_amount_unit = line.product_id.green_point_amount
                line.green_point_amount_line = line.product_id.green_point_amount
                
    def _prepare_invoice_line(self, **kwargs):
        res = super()._prepare_invoice_line(**kwargs)
        res.update({
            'green_point_amount_unit': self.green_point_amount_unit,
            'green_point_amount_line': self.green_point_amount_line,
            'green_point_source': 'sale',
        })
        return res
