# Copyright 2024 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def create_stock_orderpoint(self):
        product_supplierinfo_obj = self.env["product.supplierinfo"]
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
        for product in products:
            print("producto ::::::::::::::::::::::::::::::::::::::::::::::: ")
            print(product.name)
            for location in stock_locations:
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

            product_suppliers = product_supplierinfo_obj.search(
                [
                    ("product_id", "=", product.id)
                ]
            )
            for product_supplier in product_suppliers:
                print("precio en la relación de proveedores::::::::::::::::::::::::::::::::::::: ")
                print(product_supplier.price)
                print("precio en el producto:::::::::::::::::::::::::::::::::::::::::::::::::::: ")
                print(product.standard_price)
                if product_supplier.price != product.standard_price:
                    product_supplier.write(
                        {
                            "price": product.standard_price
                        }
                    )

    @api.model
    def _cron_stock_orderpoint_auto_create(self):
        self.create_stock_orderpoint()
