# Copyright 2020 Xtendoo (<https://xtendoo.es>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    product_classification_id = fields.Many2one(
        comodel_name="product.classification",
        string="Classification",
        help="Select a classification for this product",
        group_expand="_read_group_classification_id",
    )

    @api.model
    def _read_group_classification_id(self, classification, domain, order):
        return classification.search([])
