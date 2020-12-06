# Copyright 2020 Xtendoo (<https://xtendoo.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class ProductClassification(models.Model):
    _name = "product.classification"
    _description = "Product Classification"
    _order = "sequence, id"

    name = fields.Char(
        comodel_name="Classification Name",
        required=True,
        translate=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        help="Used to order the Classification",
        default=1,
    )
    description = fields.Text(
        translate=True,
    )
    product_ids = fields.One2many(
        comodel_name="product.template",
        inverse_name="product_classification_id",
        string="State Products",
    )
    products_count = fields.Integer(
        string="Number of products",
        compute="_compute_products_count",
    )

    @api.depends("product_ids")
    def _compute_products_count(self):
        data = self.env["product.template"].read_group(
            [("product_classification_id", "in", self.ids)],
            ["product_classification_id"],
            ["product_classification_id"],
        )
        mapped_data = {
            record["product_classification_id"][0]: record["product_classification_id_count"]
            for record in data
        }
        for classification in self:
            classification.products_count = mapped_data.get(classification.id, 0)
