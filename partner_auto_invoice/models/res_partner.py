from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    auto_invoice = fields.Boolean(string="Auto invoice")

