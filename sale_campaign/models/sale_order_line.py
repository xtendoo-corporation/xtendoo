from odoo import api, models, fields


class OrderLine(models.Model):
    _inherit = "sale.order.line"
    _order = 'sequence'

    bonus = fields.Boolean(
        string='Bonus',
        default=False)
    promotion_ids = fields.Many2many(
        comodel_name='sale.promotion',
        string='Promotion')
    promotion = fields.Boolean(
        string='In promotion',
        default=False)

    @api.multi
    def apply_promotions(self, promotion):
        for promotion in promotion:
            self.apply_promotion(promotion)

    @api.multi
    def apply_promotion(self, promotion):
        if promotion.type == 'add':
            self.apply_promotion_add(promotion)
        elif promotion.type in ['discount', 'price_unit']:
            self.apply_promotion_discount_price(
                promotion, promotion.type)
        elif promotion.type == 'discount_last':
            self.apply_promotion_free_last(promotion)

    @api.multi
    def apply_promotion_add(self, promotion):
        total_sale_qty = sum(self.mapped('product_uom_qty'))
        (qty, value) = promotion.get_value(total_sale_qty)
        free_qty = qty and \
            (total_sale_qty // qty
             ) * value
        if free_qty:
            product_id = promotion.apply_to_same_product and \
                self[0].product_id.id or promotion.product_id.id
            line_to_add = self[-1]
            line_to_add.copy({
                'order_id': line_to_add.order_id.id,
                'sequence': line_to_add.sequence + 1,
                'product_id': product_id,
                'product_uom_qty': free_qty,
                'price_unit': 0,
                'discount': 0
            })

    @api.multi
    def apply_promotion_discount_price(self, promotion, type):
        (qty, value) = promotion.get_value(sum(self.mapped('product_uom_qty')))
        # TODO: check price
        if not value:
            return False
        values = {type: value}
        if promotion.apply_to_same_product:
            order_lines = self
        else:
            order_lines = promotion.get_apply_to_order_lines(
                self.order_id.order_line)
        for order_line in order_lines:
            if promotion.force_pricelist_price:
                values.update({'price_unit': order_line.product_id.price_unit})
            order_line.write(values)

    @api.multi
    def apply_promotion_other(self, promotion):
        value = promotion.get_value(sum(self.mapped('product_uom_qty')))
        if value:
            self.order_id.filtered(
                lambda l: (l.product_id == promotion.product_id or
                           (l.product_id.product_tmpl_id == promotion.product_tmpl_id))
            ).write({'discount': promotion.amount})

    @api.multi
    def apply_promotion_bonus(self, promotion):
        pass

    @api.multi
    def apply_promotion_free_last(self, promotion):
        pass
