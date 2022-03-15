from odoo import api, fields, models

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    sale_line_discount_ids = fields.Many2many(string="Inline Discount", comodel_name='sale.inline.discount'
                                          )

    @api.onchange('sale_line_discount_ids')
    def onchange_sale_discount_global_ids(self):
        percentage = 0.00
        for discount in self.sale_line_discount_ids:
            percentage += discount.percentage
        self.discount = percentage

    @api.onchange('product_id')
    def _onchange_discount(self):
        if self.order_id.partner_id.sale_line_discount_ids:
            self.sale_line_discount_ids = self.order_id.partner_id.sale_line_discount_ids
            self.onchange_sale_discount_global_ids()


    def _prepare_invoice_line(self):
        res = super()._prepare_invoice_line()
        if not res.get('account_line_discount_ids'):
            res['account_line_discount_ids'] = self.sale_line_discount_ids
        return res
