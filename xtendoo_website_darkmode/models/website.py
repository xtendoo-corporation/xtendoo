import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


HEX_COLOR_RE = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')


class Website(models.Model):
    _inherit = 'website'

    xtendoo_darkmode_enabled = fields.Boolean(
        string='Activar modo oscuro',
        default=True,
        help='Permite mostrar el toggle de modo oscuro/claro en la cabecera de la website.',
    )
    xtendoo_darkmode_default_mode = fields.Selection(
        selection=[
            ('light', 'Claro'),
            ('dark', 'Oscuro'),
            ('system', 'Seguir sistema'),
        ],
        string='Modo inicial',
        default='system',
        required=True,
        help='Modo aplicado por defecto antes de que el visitante elija su preferencia.',
    )
    xtendoo_darkmode_background_color = fields.Char(
        string='Color de fondo',
        default='#121212',
        required=True,
    )
    xtendoo_darkmode_text_color = fields.Char(
        string='Color de texto',
        default='#F5F5F5',
        required=True,
    )
    xtendoo_darkmode_link_color = fields.Char(
        string='Color de enlaces',
        default='#8AB4F8',
        required=True,
    )
    xtendoo_darkmode_header_background_color = fields.Char(
        string='Color de fondo de cabecera',
        default='#1F2937',
        required=True,
    )
    xtendoo_darkmode_header_text_color = fields.Char(
        string='Color de texto de cabecera',
        default='#FFFFFF',
        required=True,
    )

    @api.model
    def _xtendoo_darkmode_palette_fields(self):
        return {
            'background': ('xtendoo_darkmode_background_color', '#121212', _('Color de fondo')),
            'text': ('xtendoo_darkmode_text_color', '#F5F5F5', _('Color de texto')),
            'link': ('xtendoo_darkmode_link_color', '#8AB4F8', _('Color de enlaces')),
            'header_background': ('xtendoo_darkmode_header_background_color', '#1F2937', _('Color de fondo de cabecera')),
            'header_text': ('xtendoo_darkmode_header_text_color', '#FFFFFF', _('Color de texto de cabecera')),
        }

    @api.model
    def _xtendoo_normalize_darkmode_color(self, color_value, fallback):
        color_value = (color_value or '').strip()
        if HEX_COLOR_RE.fullmatch(color_value):
            return color_value.upper()
        return fallback

    def _xtendoo_get_darkmode_palette(self):
        self.ensure_one()
        palette = {}
        for key, (field_name, fallback, _label) in self._xtendoo_darkmode_palette_fields().items():
            palette[key] = self._xtendoo_normalize_darkmode_color(self[field_name], fallback)
        return palette

    @api.constrains(
        'xtendoo_darkmode_background_color',
        'xtendoo_darkmode_text_color',
        'xtendoo_darkmode_link_color',
        'xtendoo_darkmode_header_background_color',
        'xtendoo_darkmode_header_text_color',
    )
    def _check_xtendoo_darkmode_colors(self):
        for website in self:
            for field_name, _fallback, label in website._xtendoo_darkmode_palette_fields().values():
                value = (website[field_name] or '').strip()
                if not HEX_COLOR_RE.fullmatch(value):
                    raise ValidationError(
                        _('%(label)s debe tener formato HEX, por ejemplo %(example)s.') % {
                            'label': label,
                            'example': '#121212',
                        }
                    )

