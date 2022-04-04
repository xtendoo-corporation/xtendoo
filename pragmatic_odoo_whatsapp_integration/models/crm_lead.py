# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
import requests
import json
from odoo.exceptions import UserError
import re
import logging
_logger = logging.getLogger(__name__)


class CRMLead(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def create(self, vals):
        res = super(CRMLead, self).create(vals)
        try:
            res.send_message_on_whatsapp()
        except Exception as e_log:
            _logger.exception("Exception in creating lead  %s:\n", str(e_log))
        return res

    def cleanhtml(self, raw_html):
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext

    def convert_to_html(self, message):
        for data in re.findall(r'\*.*?\*', message):
            message = message.replace(data, '<span style="font-weight:bolder">' + data.strip('*') + '</span>')
        return message

    def send_message_on_whatsapp(self):
        Param = self.env['res.config.settings'].sudo().get_values()
        res_partner_id = self.env['res.partner'].search([('id', '=', self.user_id.partner_id.id)])
        res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
        msg = ''
        mail_message_body = ''
        whatsapp_msg_number = res_partner_id.mobile
        if whatsapp_msg_number:
            whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
            whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(
                '+' + str(res_partner_id.country_id.phone_code), "")
            if res_partner_id.country_id.phone_code and res_partner_id.mobile:
                phone_exists_url = Param.get('whatsapp_endpoint') + '/checkPhone?token=' + Param.get( 'whatsapp_token') + \
                                   '&phone=' + str(res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                phone_exists_response = requests.get(phone_exists_url)
                json_response_phone_exists = json.loads(phone_exists_response.text)
                if (phone_exists_response.status_code == 200 or phone_exists_response.status_code == 201) and json_response_phone_exists['result'] == 'exists':
                    if self.partner_id:
                        msg += "\n*" + _("Customer") + ':* ' + self.partner_id.name
                    if self.email_from:
                        msg += '\n*' + _("Email") + ':* '+self.email_from
                    if self.phone:
                        msg += '\n*' + _("Phone") + ':* '+self.phone
                    if self.date_deadline:
                        msg += '\n*' + _("Expected closing date") + ':* '+str(self.date_deadline)
                    if self.description:
                        msg += '\n*' + _("Description") + ':* ' +str(self.description)
                    msg = _('Hello') + ' ' + res_partner_id.name+','+ '\n' + _("New lead assigned to you") + '\n*' + _("Lead name") + ':* '+self.name+""+msg
                    if res_user_id:
                        if res_user_id.has_group('pragmatic_odoo_whatsapp_integration.group_crm_enable_signature'):
                            user_signature = self.cleanhtml(res_user_id.signature)
                            msg += "\n\n" + user_signature
                    url = Param.get('whatsapp_endpoint') + '/sendMessage?token=' + Param.get('whatsapp_token')
                    headers = {"Content-Type": "application/json"}
                    tmp_dict = {
                        "phone": "+" + str(res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                        "body": msg
                    }
                    response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                    if response.status_code == 201 or response.status_code == 200:
                        _logger.info("\nSend Message successfully")
                        mail_message_obj = self.env['mail.message']
                        if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_crm_display_chatter_message'):
                            mail_message_body = """<p style='margin:0px; font-size:13px; font-family:"Lucida Grande", Helvetica, Verdana, Arial, sans-serif'><img src="/web_editor/font_to_img/62002/rgb(73,80,87)/13" data-class="fa fa-whatsapp" style="border-style:none; vertical-align:middle; height:auto; width:auto" width="0" height="0"></p>"""
                            mail_message_body += msg
                            body_msg = self.convert_to_html(mail_message_body)
                            body_mail_msg = "<br />".join(body_msg.split("\n"))
                            mail_message_id = mail_message_obj.sudo().create({
                                'res_id': self.id,
                                'model': 'crm.lead',
                                'body': body_mail_msg,
                            })
                else:
                    raise UserError(_('Please add valid whatsapp number for %s ') % res_partner_id.name)
            else:
                raise UserError(_('Please enter partner mobile number or select country for partner'))
