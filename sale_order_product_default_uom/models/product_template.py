from odoo import api, fields, models


class ProductTemplate(models.Model):
<<<<<<< HEAD
    _inherit = 'product.template'


    uom_qty = fields.Float(
        string="Sale default units",
        default=1.00
    )

=======
    _inherit = "product.template"

    uom_qty = fields.Float(
        string="Sale default units", digits="Product Unit of Measure",
    )
>>>>>>> 95fb20d3cde5b134ce9d049d5b7cf09b7f6ce708
