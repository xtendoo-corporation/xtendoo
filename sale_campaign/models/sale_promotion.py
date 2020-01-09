from odoo import models, fields, api


class SalePromotion(models.Model):
    _name = 'sale.promotion'

    name = fields.Char(
        string='Name')
    campaign_ids = fields.Many2many(
        comodel_name='sale.campaign',
        string='Campaigns')
    type = fields.Selection(
        [('discount', 'Discount'),
         ('price_unit', 'Special Price'),
         ('add', 'Add Product'),
         ('discount_last', 'Discount last product')],
        string='Type')
    apply_on = fields.Selection(
        [('product_template', 'Product Template'),
         ('product_variant', 'Product Variant'),
         ('product_category', 'Product Category'),
         ],
        string='Apply on')
    apply_on_product_tmpl_ids = fields.Many2many(
        comodel_name='product.template',
        string='Product Templates')
    apply_on_product_ids = fields.Many2many(
        comodel_name='product.product',
        string='Products')
    apply_on_category_ids = fields.Many2many(
        comodel_name='product.category',
        string='Category')
    apply_to_same_product = fields.Boolean(
        string='Apply to same product',
        default=True)
    apply_to = fields.Selection(
        [('product_template', 'Product Template'),
         ('product_variant', 'Product Variant'),
         ('product_category', 'Product Category'),
         ],
        string='Apply to')
    apply_to_product_tmpl_ids = fields.Many2many(
        comodel_name='product.template',
        string='Product Templates')
    apply_to_product_ids = fields.Many2many(
        comodel_name='product.product',
        string='Products')
    apply_to_category_ids = fields.Many2many(
        comodel_name='product.category',
        string='Category')
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product')
    promotion_qty_ids = fields.One2many(
        comodel_name='sale.promotion.qty',
        inverse_name='promotion_id',
        string='Quantities')
    promotion_product_tmpl_ids = fields.Many2many(
        comodel_name='product.template',
        string='Product Templates')
    promotion_product_ids = fields.Many2many(
        comodel_name='product.product',
        string='Products')
    promotion_category_ids = fields.Many2many(
        comodel_name='product.category',
        string='Category')
    active = fields.Boolean(
        string='Active',
        default=True)
    start_date = fields.Date(
        string='Start Date')
    end_date = fields.Date(
        string='End Date')
    force_pricelist_price = fields.Boolean(
        string='Force Pricelist Price')
    mixing_allowed = fields.Boolean(
        string='Mixing Allowed')
    excluding_promotion = fields.Boolean(
        string='Excluding Promotion',
        default=False)

    @api.multi
    def get_promotion_keys(self):
        self.ensure_one()
        if self.apply_on == 'product_template':
            return self.apply_on_product_tmpl_ids.ids
        elif self.apply_on == 'product_variant':
            return self.apply_on_product_ids.ids
        elif self.apply_on == 'product_category':
            return self.apply_on_category_ids.ids

    @api.multi
    def get_apply_to_order_lines(self, order_lines):
        self.ensure_one()
        if self.apply_to == 'product_template':
            return order_lines.filtered(
                lambda l:
                    l.product_id.product_tmpl_id in
                    self.apply_on_product_tmpl_ids)
        elif self.apply_to == 'product_variant':
            return order_lines.filtered(
                lambda l:
                    l.product_id in
                    self.apply_on_product_ids)
        elif self.apply_to == 'product_category':
            return order_lines.filtered(
                lambda l:
                    l.product_id.product_categ_id in
                    self.apply_on_category_ids)

    @api.multi
    def get_value(self, qty):
        self.ensure_one()
        values = self.promotion_qty_ids.filtered(
            lambda s: s.start <= qty
        ).mapped(lambda l: (l.start, l.value))
        return values and values[0] or (False, False)
