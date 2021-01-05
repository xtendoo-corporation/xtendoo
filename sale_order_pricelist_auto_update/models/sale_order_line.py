from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_round


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    state = fields.Selection(
        related='order_id.state'
    )
    is_pricelist_change = fields.Boolean(
        'The pricelist has changed',
        compute='_compute_is_pricelist_change',
    )

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        if not self.product_id:
            return
        if self.product_id.standard_price == 0.0:
            return
        if self.price_unit < self.product_id.standard_price:
            raise UserError(
                _('The unit price can\'t be lower than cost price %.2f') %
                (self.product_id.standard_price)
            )

    @api.depends('price_unit')
    def _compute_is_pricelist_change(self):
        precision = self.env['decimal.precision'].precision_get(
            'Payment Terms'
        )
        for line in self:
            if line.product_id:
                try:
                    display_price = line._get_display_price(line.product_id)
                    pricelist_price_unit = self.env['account.tax']._fix_tax_included_price_company(
                        display_price, line.product_id.taxes_id, line.tax_id, line.company_id
                    )
                    print("float_compare", float_compare(line.price_unit, pricelist_price_unit, precision_rounding=precision))
                    line.is_pricelist_change = ((line.price_unit - pricelist_price_unit) != 0.0)
                except:
                    line.is_pricelist_change = False
            else:
                line.is_pricelist_change = False

    def action_update_pricelist(self):
        print("action_update_pricelist*****************************************************")
        for line in self:
            items = self.env['product.pricelist.item'].search([
                ('pricelist_id', '=', line.order_id.pricelist_id.id),
                ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                ('applied_on', '=', '1_product'),
                ('compute_price', '=', 'fixed'),
            ])
            if items:
                items.write({'fixed_price': line.price_unit})
            else:
                self.env['product.pricelist.item'].create([
                    {'pricelist_id': line.order_id.pricelist_id.id,
                     'product_tmpl_id': line.product_id.product_tmpl_id.id,
                     'fixed_price': line.price_unit,
                     'applied_on': '1_product',
                     'base': 'list_price',
                     'compute_price': 'fixed'}])
