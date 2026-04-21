from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    xtendoo_darkmode_enabled = fields.Boolean(
        related='website_id.xtendoo_darkmode_enabled',
        readonly=False,
    )
    xtendoo_darkmode_default_mode = fields.Selection(
        related='website_id.xtendoo_darkmode_default_mode',
        readonly=False,
    )
    xtendoo_darkmode_background_color = fields.Char(
        related='website_id.xtendoo_darkmode_background_color',
        readonly=False,
    )
    xtendoo_darkmode_text_color = fields.Char(
        related='website_id.xtendoo_darkmode_text_color',
        readonly=False,
    )
    xtendoo_darkmode_link_color = fields.Char(
        related='website_id.xtendoo_darkmode_link_color',
        readonly=False,
    )
    xtendoo_darkmode_header_background_color = fields.Char(
        related='website_id.xtendoo_darkmode_header_background_color',
        readonly=False,
    )
    xtendoo_darkmode_header_text_color = fields.Char(
        related='website_id.xtendoo_darkmode_header_text_color',
        readonly=False,
    )

