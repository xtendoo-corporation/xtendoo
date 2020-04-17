# See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    digital_signature = fields.Binary(string='Digital signature')