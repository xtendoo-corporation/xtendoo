from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tiktok_pixel_key = fields.Char(
        related='website_id.tiktok_pixel_key',
        string='TikTok Pixel Code',
        readonly=False,
    )

    @api.depends('website_id')
    def has_tiktok_pixel(self):
        self.has_tiktok_pixel = bool(self.tiktok_pixel_key)

    def inverse_has_tiktok_pixel(self):
        if not self.has_tiktok_pixel:
            self.has_tiktok_pixel = False
            self.tiktok_pixel_key = False

    has_tiktok_pixel = fields.Boolean(
        string='TikTok Pixel',
        compute=has_tiktok_pixel,
        inverse=inverse_has_tiktok_pixel,
    )
