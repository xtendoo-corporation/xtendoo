from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    green_point_applicable = fields.Boolean(related='product_id.green_point_enabled', store=True)
    green_point_amount_unit = fields.Float(string="Importe PV (Unidad)", compute="_compute_green_point", store=True, readonly=False, digits='Product Price')
    green_point_amount_line = fields.Float(string="Importe PV (Línea)", compute="_compute_green_point", store=True, readonly=False)
    green_point_source = fields.Char(string="Origen PV", default="manual")
    green_point_in_cost = fields.Boolean(string="PV en Coste", compute="_compute_gp_in_cost", store=True, readonly=False)
    price_subtotal_with_green_point = fields.Monetary(string="Subtotal + PV", compute="_compute_price_subtotal_gp")

    @api.depends('company_id.green_point_affects_cost')
    def _compute_gp_in_cost(self):
        for line in self:
            line.green_point_in_cost = line.company_id.green_point_affects_cost

    @api.depends('price_subtotal', 'green_point_amount_line')
    def _compute_price_subtotal_gp(self):
        for line in self:
            line.price_subtotal_with_green_point = line.price_subtotal + line.green_point_amount_line

    @api.depends('product_id', 'quantity')
    def _compute_green_point(self):
        for line in self:
            if not line.product_id or not line.product_id.green_point_enabled or line.display_type not in ('product', False, ''):
                line.green_point_amount_unit = 0.0
                line.green_point_amount_line = 0.0
                continue

            # If from purchase or sales, retain calculated standard
            if line.green_point_source in ('purchase', 'sale'):
                continue

            gpt = line.product_id.green_point_type
            if gpt == 'unit':
                line.green_point_amount_unit = line.product_id.green_point_amount
                line.green_point_amount_line = line.product_id.green_point_amount * line.quantity
            elif gpt == 'line':
                line.green_point_amount_unit = line.product_id.green_point_amount
                line.green_point_amount_line = line.product_id.green_point_amount

    # Odoo 18: @api.onchange no es fiable en account.move.line porque las líneas
    # se editan en batch. Se sustituye por override de write() para garantizar
    # que el cálculo inverso (línea → unidad) se ejecute siempre.
    def write(self, vals):
        res = super().write(vals)
        if 'green_point_amount_line' in vals or 'quantity' in vals:
            for line in self:
                if (
                    line.move_id.move_type in ('in_invoice', 'in_refund', 'in_receipt')
                    and line.quantity
                    and line.green_point_amount_line
                ):
                    # Recalcular importe unitario a partir del importe de línea
                    line.green_point_amount_unit = line.green_point_amount_line / line.quantity
        return res

    @api.constrains('green_point_amount_unit', 'green_point_amount_line')
    def _check_gp_positive(self):
        if any(l.green_point_amount_unit < 0 or l.green_point_amount_line < 0 for l in self):
            raise ValidationError(_("El importe no puede ser negativo."))
