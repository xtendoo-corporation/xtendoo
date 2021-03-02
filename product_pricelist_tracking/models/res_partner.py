# Copyright 2020 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import fields, models, api


class Partner(models.Model):
    _inherit = 'res.partner'

    # NOT A REAL PROPERTY !!!!
    property_product_pricelist = fields.Many2one(
        'product.pricelist',
        'Pricelist',
        compute='_compute_product_pricelist',
        inverse="_inverse_product_pricelist",
        company_dependent=False,
        track_visibility="always",
        help="This pricelist will be used, instead of the default one, for sales to the current partner")
