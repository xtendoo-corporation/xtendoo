from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_default_pos_category_id = fields.Many2one(
        related="pos_config_id.default_pos_category_id",
        readonly=False,
    )
