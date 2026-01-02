# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class MailWhatsappTemplate(models.Model):
    _inherit = "mail.whatsapp.template"

    model_id = fields.Many2one(
        'ir.model',
        string="Model",
        required=True,
        default=lambda self: self.env.ref('base.model_res_partner').id,
        help="Model for which this template will be used (e.g., res.partner, sale.order, account.move)"
    )

    allow_attachments = fields.Boolean(
        string="Allow Attachments",
        default=True,
        help="If enabled, attachments will be sent as separate messages after the template. "
             "This works only if you're within the 24-hour customer service window."
    )
