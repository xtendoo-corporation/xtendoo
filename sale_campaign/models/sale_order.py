from odoo import models, api
import math


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def apply_promotions_multi(self):
        for order in self:
            order.apply_promotions()

    @api.multi
    def apply_promotions(self):
        self.ensure_one()
        for promotion in self.pricelist_id.get_promotions(self.partner_id):
            order_lines = self.get_keys(promotion)
            # Check promotions
            if order_lines:
                if promotion.mixing_allowed:
                    order_lines.apply_promotions(promotion)
                else:
                    for product_id in order_lines.mapped('product_id.id'):
                        order_lines_by_product = order_lines.filtered(
                            lambda l: l.product_id.id == product_id
                        )
                        order_lines_by_product.apply_promotions(promotion)

    def get_sale_keys(self, apply_on):
        self.ensure_one()
        if apply_on == 'product_template':
            return self.order_line.mapped(
                lambda l: l.product_id.product_tmpl_id.id)
        elif apply_on == 'product_variant':
            return self.order_line.mapped(
                lambda l: l.product_id.id)
        elif apply_on == 'product_category':
            return self.order_line.mapped(
                lambda l: l.product_id.categ_id.id)
        else:
            return False

    def get_sale_lines_by_keys(self, promotion, keys):
        self.ensure_one()
        if promotion.apply_on == 'product_template':
            return self.order_line.filtered(
                lambda l: l.product_id.product_tmpl_id.id in keys
            )
        elif promotion.apply_on == 'product_variant':
            return self.order_line.filtered(
                lambda l: l.product_id.id in keys
            )
        elif promotion.apply_on == 'product_category':
            return self.order_line.filtered(
                lambda l: l.product_id.categ_id.id in keys
            )
        else:
            return False

    @api.multi
    def get_keys(self, promotion):
        self.ensure_one()
        sale_key_ids = self.get_sale_keys(promotion.apply_on)
        promotion_key_ids = promotion.get_promotion_keys()
        keys = sale_key_ids and promotion_key_ids and \
            list(set(sale_key_ids) & set(promotion_key_ids))
        if keys:
            return self.get_sale_lines_by_keys(promotion, keys)
        else:
            return False
