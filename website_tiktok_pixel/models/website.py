from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    tiktok_pixel_key = fields.Char(string='TikTok Pixel Code')

    def ttp_get_keys(self):
        self.ensure_one()
        return [self.tiktok_pixel_key] if self.tiktok_pixel_key else []
