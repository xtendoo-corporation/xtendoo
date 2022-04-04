import requests
from odoo import http, _, models, api, modules
import logging
import json
from odoo.exceptions import UserError
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.web.controllers.main import ensure_db, Home, SIGN_UP_REQUEST_PARAMS

from odoo.http import request
import phonenumbers
import datetime
import time
import pytz
from odoo.tools import ustr
import requests
import base64
_logger = logging.getLogger(__name__)
from odoo.addons.phone_validation.tools import phone_validation


class SendMessage(http.Controller):
    _name = 'send.message.controller'

    def format_amount(self, amount, currency):
        fmt = "%.{0}f".format(currency.decimal_places)
        lang = http.request.env['res.lang']._lang_get(http.request.env.context.get('lang') or 'en_US')

        formatted_amount = lang.format(fmt, currency.round(amount), grouping=True, monetary=True)\
            .replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'-\N{ZERO WIDTH NO-BREAK SPACE}')
        pre = post = u''
        if currency.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=currency.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=currency.symbol or '')
        return u'{pre}{0}{post}'.format(formatted_amount, pre=pre, post=post)

    @http.route('/whatsapp/send/message', type='http', auth='user', website=True, csrf=False)
    def sale_order_paid_status(self, **post):
        pos_order = http.request.env['pos.order'].sudo().search([('pos_reference', '=', post.get('order'))])
        user_context = pos_order.env.context.copy()
        user_context.update({'lang': pos_order.partner_id.lang})
        pos_order.env.context = user_context

        context = request.env.context.copy()
        context.update({'lang': pos_order.partner_id.lang})
        request.env.context = context
        if pos_order.partner_id:
            context = request.env.context.copy()
            context.update({'lang': pos_order.partner_id.lang})
            request.env.context = context
            if pos_order.partner_id.mobile and pos_order.partner_id.country_id.phone_code:
                doc_name = _("POS")
                msg = _("Hello") + " " + pos_order.partner_id.name
                if pos_order.partner_id.parent_id:
                    msg += "(" + pos_order.partner_id.parent_id.name + ")"
                msg += "\n\n" + _("Your")+ " "
                msg += doc_name + " *" + pos_order.name + "* "
                msg += " " + _("with Total Amount") + " " + self.format_amount(pos_order.amount_total, pos_order.pricelist_id.currency_id) + "."
                msg += "\n\n" + _("Following is your order details.")
                for line_id in pos_order.lines:
                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.name + "\n*" + _("Qty") + ":* " + str(line_id.qty) + " " + "\n*" + _("Unit Price") + ":* " + str(
                        line_id.price_unit) + "\n*" + _("Subtotal")+ ":* " + str(line_id.price_subtotal)
                    msg += "\n------------------"
                Param = http.request.env['res.config.settings'].sudo().get_values()
                whatsapp_number = pos_order.partner_id.mobile
                whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
                whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(pos_order.partner_id.country_id.phone_code), "")
                phone_exists_url = Param.get('whatsapp_endpoint') + '/checkPhone?token=' + Param.get(
                    'whatsapp_token') + '&phone=' + str(pos_order.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                phone_exists_response = requests.get(phone_exists_url)
                json_response_phone_exists = json.loads(phone_exists_response.text)
                if (phone_exists_response.status_code == 200 or phone_exists_response.status_code == 201) and json_response_phone_exists['result'] == 'exists':
                    url = Param.get('whatsapp_endpoint') + '/sendMessage?token=' + Param.get('whatsapp_token')
                    headers = {"Content-Type": "application/json"}
                    tmp_dict = {"phone": "+" + str(pos_order.partner_id.country_id.phone_code) + "" +whatsapp_msg_number_without_code, "body": msg}
                    response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                    if response.status_code == 201 or response.status_code == 200:
                        _logger.info("\nSend Message successfully")
                        return "Send Message successfully"
                elif json_response_phone_exists.get('result') == 'not exists':
                    return "Phone not exists on whatsapp"
                else:
                    return json_response_phone_exists.get('error')


class AuthSignupHomeDerived(AuthSignupHome):

    def get_auth_signup_config(self):
        """retrieve the module config (which features are enabled) for the login page"""
        get_param = request.env['ir.config_parameter'].sudo().get_param
        countries = request.env['res.country'].sudo().search([])
        return {
            'signup_enabled': request.env['res.users']._get_signup_invitation_scope() == 'b2c',
            'reset_password_enabled': get_param('auth_signup.reset_password') == 'True',
            'countries': countries
        }

    def get_auth_signup_qcontext(self):
        SIGN_UP_REQUEST_PARAMS.add('mobile')
        qcontext = super().get_auth_signup_qcontext()
        return qcontext

    def do_signup(self, qcontext):
        """ Shared helper that creates a res.partner out of a token """
        values = self._prepare_signup_values(qcontext)
        if qcontext.get('country_id'):
            values['country_id'] = qcontext.get('country_id')
        if qcontext.get('mobile'):
            values['mobile'] = qcontext.get('mobile')
        self._signup_with_values(qcontext.get('token'), values)
        request.env.cr.commit()


class Whatsapp(http.Controller):

    def convert_epoch_to_unix_timestamp(self, msg_time):
        formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg_time))
        date_time_obj = datetime.datetime.strptime(formatted_time, '%Y-%m-%d %H:%M:%S')
        dt = False
        if date_time_obj:
            timezone = pytz.timezone(request.env['res.users'].sudo().browse([int(2)]).tz or 'UTC')
        dt = pytz.UTC.localize(date_time_obj)
        dt = dt.astimezone(timezone)
        dt = ustr(dt).split('+')[0]
        return date_time_obj

    @http.route(['/whatsapp/response/message'], type='json', auth='public')
    def whatsapp_responce(self):
        _logger.info("In whatsapp integration controller")
        data = json.loads(request.httprequest.data)
        _logger.info("data %s: ", str(data))
        _request = data
        if 'messages' in data and data['messages']:
            msg_list=[]
            msg_dict={}
            res_partner_obj = request.env['res.partner']
            whatapp_msg = request.env['whatsapp.messages']
            mail_channel_obj = request.env['mail.channel']
            mail_message_obj = request.env['mail.message']
            project_task_stage_personal_obj = request.env['project.task.stage.personal']

            for msg in data['messages']:
                if 'quotedMsgId' in msg and msg['quotedMsgId']:
                    project_task_stage_personal_id = project_task_stage_personal_obj.sudo().search([('whatsapp_msg_id', '=', msg['quotedMsgId'])])
                    if 'chatId' in msg and msg['chatId']:
                        chat_id = msg['chatId']
                        chatid_split = chat_id.split('@')
                        mobile = '+' + chatid_split[0]
                        mobile_coutry_code = phonenumbers.parse(mobile, None)
                        mobile_number = mobile_coutry_code.national_number
                        country_code = mobile_coutry_code.country_code
                        res_country_id = request.env['res.country'].sudo().search([('phone_code', '=', country_code)], limit=1)
                        reg_sanitized_number = phone_validation.phone_format(str(mobile_number), res_country_id.code, country_code)
                        res_partner_obj = res_partner_obj.sudo().search([('mobile', '=', reg_sanitized_number)], limit=1)
                        mail_message_id = mail_message_obj.sudo().search([('whatsapp_message_id', '=',msg['quotedMsgId'])], limit=1)
                        if mail_message_id.model == 'mail.channel' and mail_message_id.res_id:
                            channel_id = mail_channel_obj.sudo().search([('id', '=', mail_message_id.res_id)])
                            channel_id.with_context(from_odoobot=True).message_post(body=msg['body'], message_type="notification",
                                                                                    subtype_xmlid="mail.mt_comment", author_id=res_partner_obj.id)
                            mail_message_id.with_context(from_odoobot=True)
                    if project_task_stage_personal_id:
                        if msg.get('body') == 'done' or msg.get('body') == 'Done':
                            stage_done_id = request.env.ref('pragmatic_odoo_whatsapp_integration.whatsapp_done_project_task_type')
                            project_task_stage_personal_id.task_id.write({'stage_id': stage_done_id.id})

                elif 'chatId' in msg and msg['chatId']:
                    if '@c.us' in msg['chatId']:    #@c.us is for contacts & @g.us is for group
                        res_partner_obj = res_partner_obj.sudo().search([('chatId','=',msg['chatId'])], limit=1)
                        msg_dict = {
                            'name': msg['body'],
                            'message_id': msg['id'],
                            'fromMe': msg['fromMe'],
                            'to': msg['chatName'] if msg['fromMe'] == True else 'To Me',
                            'chatId': msg['chatId'],
                            'type': msg['type'],
                            'senderName': msg['senderName'],
                            'chatName': msg['chatName'],
                            'author': msg['author'],
                            'time': self.convert_epoch_to_unix_timestamp(msg['time']),
                            'state': 'sent' if msg['fromMe'] == True else 'received',
                        }
                        if res_partner_obj:
                            if msg['type'] == 'image' and res_partner_obj:
                                url = msg['body']
                                image_data = base64.b64encode(requests.get(url.strip()).content).replace(b'\n', b'')
                                msg_dict.update({'message_body': msg['caption'], 'msg_image':image_data, 'partner_id': res_partner_obj.id,
                                })
                            if res_partner_obj and msg['type'] == 'chat' or msg['type'] == 'video' or msg['type'] == 'audio':
                                msg_dict.update({'message_body': msg['body'], 'partner_id': res_partner_obj.id })
                            if msg['type'] == 'document' and res_partner_obj:
                                msg_dict.update({'message_body': msg['caption'], 'partner_id': res_partner_obj.id })
                        else:
                            chat_id = msg['chatId']
                            chatid_split = chat_id.split('@')
                            mobile = '+'+chatid_split[0]
                            mobile_coutry_code = phonenumbers.parse(mobile,None)
                            mobile_number = mobile_coutry_code.national_number
                            res_partner_obj = res_partner_obj.sudo().search([('mobile','=',mobile_number)], limit=1)
                            if not res_partner_obj:
                                mobile_coutry_code = phonenumbers.parse(mobile, None)
                                mobile_number = mobile_coutry_code.national_number
                                country_code = mobile_coutry_code.country_code
                                mobile = '+'+str(country_code)+' '+str(mobile_number)
                                res_partner_obj = res_partner_obj.sudo().search([('mobile', '=', mobile)], limit=1)
                            if not res_partner_obj:
                                mobile_coutry_code = phonenumbers.parse(mobile, None)
                                mobile_number = mobile_coutry_code.national_number
                                country_code = mobile_coutry_code.country_code
                                res_country_id = request.env['res.country'].sudo().search([('phone_code', '=', country_code)], limit=1)
                                reg_sanitized_number = phone_validation.phone_format(str(mobile_number), res_country_id.code, country_code)
                                res_partner_obj = res_partner_obj.sudo().search([('mobile', '=', reg_sanitized_number)], limit=1)
                            if res_partner_obj:
                                res_partner_obj.chatId = chat_id
                                msg_dict.update({'message_body': msg['body'], 'partner_id': res_partner_obj.id })
                            else:
                                res_partner_dict = {}
                                if msg.get('senderName'):
                                    res_partner_dict['name'] = msg.get('senderName')
                                res_country_id = request.env['res.country'].sudo().search([('phone_code', '=', mobile_coutry_code.country_code)], limit=1)
                                if res_country_id:
                                    res_partner_dict['country_id'] = res_country_id.id
                                res_partner_dict['mobile'] = mobile
                                res_partner_dict['chatId'] = chat_id
                                res_partner_id = request.env['res.partner'].sudo().create(res_partner_dict)
                                if res_partner_id:
                                    msg_dict.update({'partner_id': res_partner_id.id})
                                    if msg['type'] == 'chat':
                                        msg_dict.update({'message_body': msg['body']})
                                    if msg['type'] == 'document' or msg['type'] == 'image' or msg['type'] == 'video' or msg['type'] == 'audio':
                                        if msg['type'] == 'video' or msg['type'] == 'audio':
                                            msg_dict.update({'message_body': msg.get('body')})
                                        elif msg['type'] == 'image':
                                            url = msg['body']
                                            image_data = base64.b64encode(requests.get(url.strip()).content).replace(b'\n', b'')
                                            msg_dict.update({'msg_image': image_data})
                                        else:
                                            msg_dict.update({'message_body': msg.get('caption')})

                        if res_partner_obj or res_partner_id:
                            partner = False
                            if res_partner_obj:
                                partner = res_partner_obj
                            elif res_partner_id:
                                partner = res_partner_id
                            self.send_notification_to_admin(partner,msg)

                        _logger.info("msg_dict %s: ", str(msg_dict))
                        if len(msg_dict) > 0:
                            msg_list.append(msg_dict)
            for msg in msg_list:
                whatapp_msg_id = whatapp_msg.sudo().search([('message_id', '=', msg.get('message_id'))])
                if whatapp_msg_id:
                    whatapp_msg_id.sudo().write(msg)
                    _logger.info("whatapp_msg_id %s: ", str(whatapp_msg_id))
                    if 'messages' in data and data['messages']:
                        for msg in data['messages']:
                            if whatapp_msg_id and msg['type'] == 'document':
                                msg_attchment_dict = {}
                                url = msg['body']
                                data_base64 = base64.b64encode(requests.get(url.strip()).content)
                                msg_attchment_dict = {'name': msg['caption'], 'datas': data_base64, 'type': 'binary',
                                                      'res_model': 'whatsapp.messages', 'res_id': whatapp_msg_id.id}
                                attachment_id = request.env['ir.attachment'].sudo().create(msg_attchment_dict)
                                res_update_whatsapp_msg = whatapp_msg_id.sudo().write({'attachment_id': attachment_id.id})
                                _logger.info("res_update_whatsapp_msg %s: ", str(res_update_whatsapp_msg))
                else:
                    res_whatsapp_msg = whatapp_msg.sudo().create(msg)
                    _logger.info("res_whatsapp_msg2111 %s: ", str(res_whatsapp_msg))
                    if 'messages' in data and data['messages']:
                        for msg in data['messages']:
                            if res_whatsapp_msg and msg['type'] == 'document':
                                msg_attchment_dict = {}
                                url = msg['body']
                                data_base64 = base64.b64encode(requests.get(url.strip()).content)
                                msg_attchment_dict = {'name': msg['caption'], 'datas': data_base64, 'type': 'binary',
                                                   'res_model': 'whatsapp.messages', 'res_id': res_whatsapp_msg.id}
                                attachment_id = request.env['ir.attachment'].sudo().create(msg_attchment_dict)
                                res_update_whatsapp_msg = res_whatsapp_msg.sudo().write({'attachment_id': attachment_id.id})
                                _logger.info("res_update_whatsapp_msg %s: ", str(res_update_whatsapp_msg))

            ir_module_module_id = request.env['ir.module.module'].sudo().search(
                [('name', '=', 'pragmatic_odoo_whatsapp_marketing'), ('state', '=', 'installed')])
            if ir_module_module_id:
                self.whatsapp_marketing_bidirectional_message(data)
            else:
                return 'OK'

    def whatsapp_marketing_bidirectional_message(self, data):
        _logger.info("In whatsapp integration marketing controller")
        if 'messages' in data and data['messages']:
            msg_dict = {}
            whatsapp_contact_obj = request.env['whatsapp.contact']
            whatsapp_group_obj = request.env['whatsapp.group']
            whatapp_msg = request.env['whatsapp.messages']
            for msg in data['messages']:
                if 'chatId' in msg and msg['chatId']:
                    whatsapp_contact_obj = whatsapp_contact_obj.sudo().search([('whatsapp_id', '=', msg['chatId'])], limit=1)
                    whatsapp_group_obj = whatsapp_group_obj.sudo().search([('group_id', '=', msg['chatId'])],limit=1)
                    if whatsapp_contact_obj:
                        msg_dict = {'whatsapp_contact_id': whatsapp_contact_obj.id}
                    if whatsapp_group_obj:
                        msg_dict = {'whatsapp_group_id': whatsapp_group_obj.id }
                    _logger.info("In whatsapp integration marketing msg_dict %s: ", str(msg_dict))
                    if len(msg_dict) > 0:
                        whatapp_msg_id = whatapp_msg.sudo().search([('message_id', '=', msg['id'])])
                        if whatapp_msg_id:
                            whatapp_msg_id.sudo().write(msg_dict)
        return 'OK'

    def send_notification_to_admin(self,partner,msg):
        mail_channel_obj = request.env['mail.channel']
        whatsapp_chat_ids = request.env.ref('pragmatic_odoo_whatsapp_integration.group_whatsapp_chat')
        whatsapp_chat_users_ids = whatsapp_chat_ids.sudo().users
        whatsapp_partner_ids = whatsapp_chat_users_ids.mapped('partner_id')
        if partner:
            channel_exist = mail_channel_obj.sudo().search([('channel_partner_ids', '=', partner.id)], limit=1)
            if channel_exist:
                channel_exist.with_context(from_odoobot=True).message_post(body=msg['body'],
                                                                           message_type="notification",
                                                                           subtype_xmlid="mail.mt_comment",
                                                                           author_id=partner.id)
            else:
                image_path = modules.get_module_resource('pragmatic_odoo_whatsapp_integration', 'static/img',
                                                         'whatsapp_logo.png')
                image = base64.b64encode(open(image_path, 'rb').read())
                partner_list = []
                for whatsapp_chat_partner_id in whatsapp_partner_ids:
                    partner_list.append(whatsapp_chat_partner_id.id)
                partner_list.append(partner.id)
                if len(partner_list) > 0:
                    channel_dict = {
                        'name': 'Chat with {}'.format(partner.name),
                        'channel_partner_ids': [(6, 0, partner_id) for partner_id in partner_list],
                        # 'public': 'private',
                        'image_128':image,
                    }
                    channel = mail_channel_obj.sudo().create(channel_dict)
                    channel.with_context(from_odoobot=True).message_post(body=msg['body'],
                                                                         message_type="notification",
                                                                         subtype_xmlid="mail.mt_comment",
                                                                         author_id=partner.id)