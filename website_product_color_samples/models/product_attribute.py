# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductAttribute(models.Model):
    _inherit = "product.attribute"


    display_type = fields.Selection(
        selection_add=[("image", "Image")],
        ondelete={"image": lambda recs: recs.write({"display_type": "radio"})},
    )
