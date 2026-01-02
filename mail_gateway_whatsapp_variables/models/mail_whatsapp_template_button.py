# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MailWhatsappTemplateButton(models.Model):
    _name = "mail.whatsapp.template.button"
    _description = "WhatsApp Template Button"
    _order = "sequence, id"

    template_id = fields.Many2one(
        'mail.whatsapp.template',
        string="Template",
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string="Sequence", default=10)
    name = fields.Char(string="Button Text", required=True)
    button_type = fields.Selection([
        ('quick_reply', 'Quick Reply'),
        ('phone_number', 'Call Phone Number'),
        ('url', 'Visit Website'),
    ], string="Type", required=True, default='quick_reply')

    call_number = fields.Char(
        string="Phone Number",
        help="Phone number for call button"
    )
    website_url = fields.Char(
        string="Website URL",
        help="URL for website button"
    )
    url_type = fields.Selection([
        ('static', 'Static'),
        ('dynamic', 'Dynamic'),
    ], string="URL Type", default='static')

    @api.constrains('button_type', 'call_number', 'website_url')
    def _check_button_fields(self):
        """Validar que los campos requeridos estén presentes según el tipo de botón"""
        for button in self:
            if button.button_type == 'phone_number' and not button.call_number:
                raise ValidationError("Phone number is required for phone_number button type")
            if button.button_type == 'url' and not button.website_url:
                raise ValidationError("Website URL is required for url button type")

    @api.onchange('button_type')
    def _onchange_button_type(self):
        """Limpiar campos no necesarios cuando cambia el tipo de botón"""
        if self.button_type == 'quick_reply':
            self.call_number = False
            self.website_url = False
            self.url_type = False
        elif self.button_type == 'phone_number':
            self.website_url = False
            self.url_type = False
        elif self.button_type == 'url':
            self.call_number = False
            if not self.url_type:
                self.url_type = 'static'
