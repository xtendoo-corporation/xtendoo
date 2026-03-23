from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    green_point_applicable = fields.Boolean(related='product_id.green_point_enabled', store=True)
    green_point_amount_unit = fields.Float(string="Importe PV (Unidad)", compute="_compute_green_point", store=True, readonly=False, digits='Product Price')
    green_point_amount_line = fields.Float(string="Importe PV (Línea)", compute="_compute_green_point", store=True, readonly=False)
    green_point_manual = fields.Boolean(string="PV Manual", default=False)

    @api.depends('product_id', 'product_qty', 'green_point_manual')
    def _compute_green_point(self):
        for line in self:
            if not line.product_id or not line.product_id.green_point_enabled or line.display_type not in ('product', False, ''):
                line.green_point_amount_unit = 0.0
                line.green_point_amount_line = 0.0
                line.green_point_manual = False
                continue
            
            if line.green_point_manual:
                continue

            gpt = line.product_id.green_point_type
            if gpt == 'unit':
                line.green_point_amount_unit = line.product_id.green_point_amount
                line.green_point_amount_line = line.product_id.green_point_amount * line.product_qty
            elif gpt == 'line':
                line.green_point_amount_unit = line.product_id.green_point_amount
                line.green_point_amount_line = line.product_id.green_point_amount

    @api.constrains('green_point_amount_unit', 'green_point_amount_line')
    def _check_gp_positive(self):
        if any(l.green_point_amount_unit < 0 or l.green_point_amount_line < 0 for l in self):
            raise ValidationError(_("El importe de Punto Verde no puede ser negativo."))
            
    @api.onchange('green_point_amount_line', 'product_qty')
    def _onchange_green_point_amount_line(self):
        """ Auto-calculate unit from line if user inputs line manually. """
        if self.green_point_amount_line and self.product_qty:
            self.green_point_amount_unit = self.green_point_amount_line / self.product_qty

    def _prepare_account_move_line(self, **kwargs):
        res = super()._prepare_account_move_line(**kwargs)
        res.update({
            'green_point_amount_unit': self.green_point_amount_unit,
            'green_point_amount_line': self.green_point_amount_line,
            'green_point_source': 'purchase',
        })
        return res
