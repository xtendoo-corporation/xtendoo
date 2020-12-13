from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    move_product_qty = fields.Float(
        compute='_compute_move_waiting_product_qty',
        string='Pickings'
    )

    def _compute_move_waiting_product_qty(self):
        self.move_product_qty = 0
        for template in self:
            template.move_product_qty = float_round(sum([p.move_product_qty for p in template.product_variant_ids]),
                                                    precision_rounding=template.uom_id.rounding)
