from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    amount_total_green_point = fields.Monetary(string="Total Punto Verde", compute="_compute_green_point_totals", store=True)
    amount_untaxed_with_green_point = fields.Monetary(string="Base Imponible + PV", compute="_compute_green_point_totals", store=True)

    @api.depends('order_line.green_point_amount_line', 'amount_untaxed')
    def _compute_green_point_totals(self):
        for order in self:
            gp_total = sum(order.order_line.filtered(lambda l: l.display_type in ('product', False, '')).mapped('green_point_amount_line'))
            order.amount_total_green_point = gp_total
            order.amount_untaxed_with_green_point = order.amount_untaxed + gp_total
