# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


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

