from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"


    @api.model
    def _default_pricelist(self):
        print("*"*80)
        print(self.order_id.pricelist_id)
        print("*"*80)
        return self.order_id.pricelist_id

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
        readonly=True,
        # default=lambda self: self._default_pricelist(),
    )

