from odoo import api, fields, models, _
import requests
import json
import logging
import re
from odoo import tools
_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError


class mailChannel(models.Model):
    _inherit = 'mail.channel'

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *, message_type='notification', **kwargs):
        message = super(mailChannel, self).message_post(**kwargs)
        if not self._context.get('from_odoobot'):
            self.send_whatsapp_message(self.channel_partner_ids, kwargs, message)
        return message

    def convert_email_from_to_name(self, str1):
        result = re.search('"(.*)"', str1)
        return result.group(1)

    def custom_html2plaintext(self, html):
        html = re.sub('<br\s*/?>', '\n', html)
        html = re.sub('<.*?>', ' ', html)
        return html

    def send_whatsapp_message(self, partner_ids, kwargs, message_id):
        if 'author_id' in kwargs and kwargs.get('author_id'):
            partner_id = self.env['res.partner'].search([('id', '=', kwargs.get('author_id'))])
            param = self.env['res.config.settings'].sudo().get_values()
            no_phone_partners = []
            invalid_whatsapp_number_partner = []
            if param.get('whatsapp_endpoint') and param.get('whatsapp_token'):
                status_url = param.get('whatsapp_endpoint') + '/status?token=' + param.get('whatsapp_token')
                status_response = requests.get(status_url)
                json_response_status = json.loads(status_response.text)
                if (status_response.status_code == 200 or status_response.status_code == 201) and json_response_status['accountStatus'] == 'authenticated':
                    if partner_id.country_id.phone_code and partner_id.mobile:
                        whatsapp_msg_number = partner_id.mobile
                        whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "");
                        whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(
                            '+' + str(partner_id.country_id.phone_code), "")
                        phone_exists_url = param.get('whatsapp_endpoint') + '/checkPhone?token=' + param.get('whatsapp_token') + '&phone=' + str(partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                        phone_exists_response = requests.get(phone_exists_url)
                        json_response_phone_exists = json.loads(phone_exists_response.text)
                        if (phone_exists_response.status_code == 200 or phone_exists_response.status_code == 201) and json_response_phone_exists['result'] == 'exists':
                            _logger.info("\nPartner phone exists")
                            url = param.get('whatsapp_endpoint') + '/sendMessage?token=' + param.get('whatsapp_token')
                            headers = { "Content-Type": "application/json" }
                            html_to_plain_text = self.custom_html2plaintext(kwargs.get('body'))
                            if kwargs.get('email_from'):
                                if '<' in kwargs.get('email_from') and '>' in kwargs.get('email_from'):
                                    tmp_dict = {
                                        "phone": "+" + str(partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                        "body": self.convert_email_from_to_name(kwargs.get('email_from'))+''+ str(self.id) + ': '+ html_to_plain_text
                                    }
                                else:
                                    tmp_dict = {
                                        "phone": "+" + str(partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                        "body": kwargs.get('email_from')+ '' + str(self.id) + ': ' + html_to_plain_text
                                    }
                            else:
                                tmp_dict = {
                                    "phone": "+" + str(partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                    "body": html_to_plain_text
                                }
                            response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                            if response.status_code == 201 or response.status_code == 200:
                                _logger.info("\nSend Message successfully")
                                response_dict = response.json()
                                message_id.with_context({'from_odoobot': True}).write({'whatsapp_message_id': response_dict.get('id')})
                        else:
                            invalid_whatsapp_number_partner.append(partner_id.name)
                    else:
                        no_phone_partners.append(partner_id.name)
                else:
                    raise UserError(_('Please authorize your mobile number with chat api'))
            if len(invalid_whatsapp_number_partner) >= 1:
                raise UserError(_('Please add valid whatsapp number for %s customer')% ', '.join(invalid_whatsapp_number_partner))
        else:
            param = self.env['res.config.settings'].sudo().get_values()
            no_phone_partners = []
            invalid_whatsapp_number_partner = []
            for partner_id in partner_ids:
                if param.get('whatsapp_endpoint') and param.get('whatsapp_token'):
                    status_url = param.get('whatsapp_endpoint') + '/status?token=' + param.get('whatsapp_token')
                    status_response = requests.get(status_url)
                    json_response_status = json.loads(status_response.text)
                    if (status_response.status_code == 200 or status_response.status_code == 201) and json_response_status[
                        'accountStatus'] == 'authenticated':
                        if partner_id.country_id.phone_code and partner_id.mobile:
                            whatsapp_msg_number = partner_id.mobile
                            whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "");
                            whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(partner_id.country_id.phone_code), "")
                            phone_exists_url = param.get('whatsapp_endpoint') + '/checkPhone?token=' + param.get('whatsapp_token') + '&phone=' + str(
                                partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                            phone_exists_response = requests.get(phone_exists_url)
                            json_response_phone_exists = json.loads(phone_exists_response.text)
                            if (phone_exists_response.status_code == 200 or phone_exists_response.status_code == 201) and \
                                    json_response_phone_exists['result'] == 'exists':
                                _logger.info("\nPartner phone exists")
                                url = param.get('whatsapp_endpoint') + '/sendMessage?token=' + param.get('whatsapp_token')
                                headers = { "Content-Type": "application/json"}
                                html_to_plain_text = self.custom_html2plaintext(kwargs.get('body'))
                                if kwargs.get('email_from'):
                                    if '<' in kwargs.get('email_from') and '>' in kwargs.get('email_from'):
                                        tmp_dict = {
                                            "phone": "+" + str(partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                            "body": self.convert_email_from_to_name(kwargs.get('email_from')) + '' + str(self.id) + ': ' + html_to_plain_text
                                        }
                                    else:
                                        tmp_dict = {
                                            "phone": "+" + str(partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                            "body": kwargs.get('email_from') + '' + str(self.id) + ': ' + html_to_plain_text
                                        }
                                else:
                                    tmp_dict = {
                                        "phone": "+" + str(partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                        "body": html_to_plain_text
                                    }
                                response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                                if response.status_code == 201 or response.status_code == 200:
                                    _logger.info("\nSend Message successfully")
                                    response_dict = response.json()
                                    message_id.with_context({'from_odoobot': True}).write({'whatsapp_message_id': response_dict.get('id')})
                            else:
                                invalid_whatsapp_number_partner.append(partner_id.name)
                        else:
                            no_phone_partners.append(partner_id.name)
                    else:
                        raise UserError(_('Please authorize your mobile number with chat api'))

        if len(invalid_whatsapp_number_partner) >= 1:
            raise UserError(
                _('Please add valid whatsapp number for %s customer') % ', '.join(invalid_whatsapp_number_partner))
