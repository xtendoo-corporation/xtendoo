from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    replace_standard_wizard = fields.Boolean(config_parameter='garazd_product_label.replace_standard_wizard')  # flake8: noqa: E501
