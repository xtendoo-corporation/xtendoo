# Copyright 2024 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def create_stock_orderpoint(self):
        print("Create_stock_orderpoint*******************************")
        stock_warehouse_orderpoint_obj = self.env["stock.warehouse.orderpoint"]
        stock_locations = self.env["stock.location"].search(
            [
                ("usage", "=", "internal"),
                ("replenish_location", "=", "True"),
                ("company_id", "=", self.env.company.id),
            ]
        )
        products = self.search(
            [
                ("detailed_type", "=", "product"),
            ]
        )

        print("stock_locations: ", stock_locations)
        print("products: ", products)

        for product in products:
            for location in stock_locations:

                print("location ware house: ", location.warehouse_id)

                if not stock_warehouse_orderpoint_obj.search(
                    [
                        ("product_id", "=", product.id),
                        ("location_id", "=", location.id),
                    ]
                ):
                    stock_warehouse_orderpoint_obj.create(
                        {
                            "product_id": product.id,
                            "product_min_qty": 0,
                            "product_max_qty": 0,
                            "product_uom": product.uom_id.id,
                            "warehouse_id": location.warehouse_id.id,
                            "location_id": location.id,
                        }
                    )

    @api.model
    def _cron_stock_orderpoint_auto_create(self):
        print("Cron: stock_orderpoint_auto_create*******************************")
        self.create_stock_orderpoint()
