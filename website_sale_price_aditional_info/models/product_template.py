# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

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
        if product_id:
            product_product = self.env["product.product"].browse(product_id)
            if product_product and product_product.website_price_additional_info:
                combination_info.update(
                    {
                        "website_price_additional_info": product_product.website_price_additional_info,
                    }
                )
            else:
                combination_info.update(
                    {
                        "website_price_additional_info": "",
                    }
                )
        else:
            combination_info.update(
                {
                    "website_price_additional_info": "",
                }
            )
        return combination_info


