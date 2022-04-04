# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
import requests
import json
import datetime
_logger = logging.getLogger(__name__)


class accountInvoice(models.Model):
    _inherit = 'account.move'

    def _payment_remainder_send_message(self):
        account_invoice_ids = self.env['account.move'].search([('state', '=', 'posted'), ('move_type', '=', 'out_invoice'), ('payment_state', '=', 'not_paid'), ('invoice_date_due', '<', datetime.datetime.now())])
        Param = self.env['res.config.settings'].sudo().get_values()
        for account_invoice_id in account_invoice_ids:
            if account_invoice_id.partner_id.country_id.phone_code and account_invoice_id.partner_id.mobile:
                msg = _("Hello") + " " + account_invoice_id.partner_id.name + "\n" + _("Your invoice")
                if account_invoice_id.state == 'draft':
                    msg += " *" + _("draft") + "* "
                else:
                    msg += " *" + account_invoice_id.name + "* "
                msg += _("is pending")
                msg += "\n" + _("Total Amount") + ": " + self.env['whatsapp.msg'].format_amount(account_invoice_id.amount_total, account_invoice_id.currency_id) + " & " + _("Due Amount") + ": " + str(
                    round(account_invoice_id.partner_id.credit, 2)) + "."
                whatsapp_msg_number = account_invoice_id.partner_id.mobile
                whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(account_invoice_id.partner_id.country_id.phone_code), "")
                try:
                    url = Param.get('whatsapp_endpoint') + '/sendMessage?token=' + Param.get('whatsapp_token')
                    headers = {"Content-Type": "application/json" }
                    phone = "+" + str(account_invoice_id.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                    tmp_dict = { "phone": phone, "body": msg }
                    response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                    if response.status_code == 201 or response.status_code == 200:
                        _logger.info("\nSend Message successfully")
                        mail_message_obj = self.env['mail.message']
                        mail_message_id = mail_message_obj.sudo().create({
                            'res_id': account_invoice_id.id,
                            'model': 'account.move',
                            'body': msg,
                        })
                except Exception as e_log:
                    _logger.exception("Exception in payment remainder %s:\n", str(e_log))
