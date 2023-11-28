# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ProductTemplateAttributeValueSequence(models.Model):
    _inherit = "product.template.attribute.value"
    _order = 'sequence, id'

    sequence = fields.Integer()
