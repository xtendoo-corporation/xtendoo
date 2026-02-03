from odoo import fields, models

class CalendarAlarm(models.Model):
    _inherit = 'calendar.alarm'

    alarm_type = fields.Selection(
        selection_add=[('whatsapp', 'WhatsApp')],
        ondelete={'whatsapp': 'cascade'}
    )
    whatsapp_template_id = fields.Many2one(
        'mail.whatsapp.template',
        string="WhatsApp Template",
        domain=[('model', '=', 'calendar.alarm')],
        help="Template used to send the WhatsApp reminder."
    )
