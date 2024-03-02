from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    facebook_pixel_key = fields.Char('Facebook Pixel ID')

    def _fbp_params(self):
        self.ensure_one()
        return [{
            'action': 'init',
            'key': self.facebook_pixel_key or '',
            'extra_vals': {},
        }]

    def fbp_get_primary_key(self):
        self.ensure_one()
        return self.facebook_pixel_key or ''
