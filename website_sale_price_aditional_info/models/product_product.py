# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = "product.product"

    website_price_additional_info = fields.Text(
        string="Price additional info",
        help="When you want to show additional info about the price on the website.",
        translate=True,
    )

    def _get_combination_info(
        self,
        combination=False,
        product_id=False,
        add_qty=1,
        pricelist=False,
        parent_combination=False,
        only_template=False,
    ):
        combination_info = super()._get_combination_info(
            combination=combination,
            product_id=product_id,
            add_qty=add_qty,
            pricelist=pricelist,
            parent_combination=parent_combination,
            only_template=only_template,
        )
        combination_info.update(
            {
                "website_price_additional_info": self.website_price_additional_info,
            }
        )
        return combination_info
