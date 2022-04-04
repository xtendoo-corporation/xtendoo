# -*- coding: utf-8 -*-
import logging
import json
import requests
from odoo import api, fields, models, _, tools
from odoo.exceptions import Warning
from odoo.exceptions import UserError
import base64
import time
import re
import uuid
from odoo.tools import groupby, formataddr
from odoo.tools.safe_eval import safe_eval, time

_logger = logging.getLogger(__name__)
try:
    import phonenumbers
    from phonenumbers.phonenumberutil import region_code_for_country_code

    _sms_phonenumbers_lib_imported = True

except ImportError:
    _sms_phonenumbers_lib_imported = False
    _logger.info(
        "The `phonenumbers` Python module is not available. "
        "Phone number validation will be skipped. "
        "Try `pip3 install phonenumbers` to install it."
    )


class ScanWAQRCode(models.TransientModel):
    _name = 'whatsapp.scan.qr'
    _description = 'Scan WhatsApp QR Code'

    def _get_default_image(self):
        Param = self.env['res.config.settings'].sudo().get_values()
        Param_set = self.env['ir.config_parameter'].sudo()
        try:
            url = Param.get('whatsapp_endpoint') + '/status?token=' + Param.get('whatsapp_token')
            response = requests.get(url)
        except Exception as e_log:
            _logger.exception(e_log)
            raise UserError(_('Please add proper whatsapp endpoint or whatsapp token'))
        json_response = json.loads(response.text)
        if response.status_code == 201 or response.status_code == 200:
            # qr_code_image
            if json_response.get('accountStatus') == 'got qr code':
                qr_code_url = Param.get('whatsapp_endpoint') + '/qr_code?token=' + Param.get('whatsapp_token')
                response_qr_code = requests.get(qr_code_url)
                img = base64.b64encode(response_qr_code.content)
                Param_set.set_param("pragmatic_odoo_whatsapp_integration.whatsapp_authenticate", True)
                return img
            elif json_response.get('accountStatus') == 'authenticated':
                raise UserError(_('QR code is already scanned from chat api'))
        elif response.status_code > 200:
            raise UserError(_('There is issue in chat api'))

    qr_code_img_data = fields.Binary(default=_get_default_image)


class SendWAMessageResPartner(models.TransientModel):
    _name = 'whatsapp.msg.res.partner'
    _description = 'Send WhatsApp Message'

    def _default_unique_user(self):
        IPC = self.env['ir.config_parameter'].sudo()
        dbuuid = IPC.get_param('database.uuid')
        return dbuuid + '_' + str(self.env.uid)

    partner_ids = fields.Many2many('res.partner', 'whatsapp_msg_res_partner_res_partner_rel', 'wizard_id', 'partner_id', 'Recipients')
    message = fields.Text('Message', required=True)
    attachment_ids = fields.Many2many('ir.attachment', 'whatsapp_msg_res_partner_ir_attachments_rel', 'wizard_id', 'attachment_id', 'Attachments')
    unique_user = fields.Char(default=_default_unique_user)

    def _phone_get_country(self, partner):
        if 'country_id' in partner:
            return partner.country_id
        return self.env.user.company_id.country_id

    def _msg_sanitization(self, partner, field_name):
        number = partner[field_name]
        if number and _sms_phonenumbers_lib_imported:
            country = self._phone_get_country(partner)
            country_code = country.code if country else None
            try:
                phone_nbr = phonenumbers.parse(number, region=country_code, keep_raw_input=True)
            except phonenumbers.phonenumberutil.NumberParseException:
                return number
            if not phonenumbers.is_possible_number(phone_nbr) or not phonenumbers.is_valid_number(phone_nbr):
                return number
            phone_fmt = phonenumbers.PhoneNumberFormat.E164
            return phonenumbers.format_number(phone_nbr, phone_fmt)
        else:
            return number

    def _get_records(self, model):
        if self.env.context.get('active_ids'):
            records = model.browse(self.env.context.get('active_ids', []))
        else:
            records = model.browse(self.env.context.get('active_id', []))
        return records

    @api.model
    def default_get(self, fields):
        result = super(SendWAMessageResPartner, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        res_id = self.env.context.get('active_id')
        rec = self.env[active_model].browse(res_id)
        Attachment = self.env['ir.attachment']
        res_name = 'Invoice_' + rec.number.replace('/', '_') if active_model == 'account.move' else rec.name.replace('/', '_')
        msg = result.get('message', '')
        result['message'] = msg

        if not self.env.context.get('default_recipients') and active_model and hasattr(self.env[active_model], '_sms_get_default_partners'):
            model = self.env[active_model]
            records = self._get_records(model)
            partners = records._sms_get_default_partners()
            phone_numbers = []
            no_phone_partners = []
            if active_model != 'res.partner':
                is_attachment_exists = Attachment.search([('res_id', '=', res_id), ('name', 'like', res_name + '%'), ('res_model', '=', active_model)], limit=1)
                if not is_attachment_exists:
                    attachments = []
                    if active_model == 'sale.order':
                        template = self.env.ref('sale.email_template_edi_sale')
                    elif active_model == 'account.move':
                        template = self.env.ref('account.email_template_edi_invoice')
                    elif active_model == 'purchase.order':
                        if self.env.context.get('send_rfq', False):
                            template = self.env.ref('purchase.email_template_edi_purchase')
                        else:
                            template = self.env.ref('purchase.email_template_edi_purchase_done')
                    elif active_model == 'stock.picking':
                        template = self.env.ref('stock.mail_template_data_delivery_confirmation')
                    elif active_model == 'account.payment':
                        template = self.env.ref('account.mail_template_data_payment_receipt')
                    report = template.report_template
                    report_service = report.report_name
                    if report.report_type not in ['qweb-html', 'qweb-pdf']:
                        raise UserError(_('Unsupported report type %s found.') % report.report_type)
                    res, format = report._render_qweb_pdf([res_id])
                    res = base64.b64encode(res)
                    if not res_name:
                        res_name = 'report.' + report_service
                    ext = "." + format
                    if not res_name.endswith(ext):
                        res_name += ext
                    attachments.append((res_name, res))
                    attachment_ids = []
                    for attachment in attachments:
                        attachment_data = {
                            'name': attachment[0],
                            'datas': attachment[1],
                            'type': 'binary',
                            'res_model': active_model,
                            'res_id': res_id,
                        }
                        attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    result['attachment_ids'] = [(6, 0, [is_attachment_exists.id])]
            for partner in partners:
                number = self._msg_sanitization(partner, self.env.context.get('field_name') or 'mobile')
                if number:
                    phone_numbers.append(number)
                else:
                    no_phone_partners.append(partner.name)
            if len(partners) > 1:
                if no_phone_partners:
                    raise UserError(_('Missing mobile number for %s.') % ', '.join(no_phone_partners))
            result['partner_ids'] = [(6, 0, partners.ids)]

            result['message'] = msg
        return result

    def action_send_msg_res_partner(self):
        Param = self.env['res.config.settings'].sudo().get_values()
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        phone_numbers = []
        no_phone_partners = []
        try:
            status_url = Param.get('whatsapp_endpoint') + '/status?token=' + Param.get('whatsapp_token')
            status_response = requests.get(status_url)
        except Exception as e_log:
            _logger.exception(e_log)
            raise UserError(_('Please add proper whatsapp endpoint or whatsapp token'))
        json_response_status = json.loads(status_response.text)
        if (status_response.status_code == 200 or status_response.status_code == 201) and json_response_status['accountStatus'] == 'authenticated':
            if active_model == 'res.partner':
                for res_partner_id in self.partner_ids:
                    number = str(res_partner_id.country_id.phone_code) + res_partner_id.mobile
                    if res_partner_id.country_id.phone_code and res_partner_id.mobile:
                        whatsapp_number = res_partner_id.mobile
                        whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
                        whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(res_partner_id.country_id.phone_code), "")
                        phone_exists_url = Param.get('whatsapp_endpoint') + '/checkPhone?token=' + Param.get('whatsapp_token') + '&phone=' + str(res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                        phone_exists_response = requests.get(phone_exists_url)
                        json_response_phone_exists = json.loads(phone_exists_response.text)
                        if (phone_exists_response.status_code == 200 or phone_exists_response.status_code == 201) and json_response_phone_exists['result'] == 'exists':
                            url = Param.get('whatsapp_endpoint') + '/sendMessage?token=' + Param.get('whatsapp_token')
                            headers = {"Content-Type": "application/json"}
                            tmp_dict = {
                                "phone": "+" + str(res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                "body": self.message}
                            response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                            if response.status_code == 201 or response.status_code == 200:
                                _logger.info("\nSend Message successfully")
                            if self.attachment_ids:
                                for attachment in self.attachment_ids:
                                    with open("/tmp/" + attachment.name, 'wb') as tmp:
                                        encoded_file = str(attachment.datas)
                                        url_send_file = Param.get('whatsapp_endpoint') + '/sendFile?token=' + Param.get('whatsapp_token')
                                        headers_send_file = {"Content-Type": "application/json"}
                                        dict_send_file = {
                                            "phone": "+" + str(res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                            "body": "data:" + attachment.mimetype + ";base64," + encoded_file[2:-1],
                                            "filename": attachment.name
                                        }
                                        response_send_file = requests.post(url_send_file, json.dumps(dict_send_file), headers=headers_send_file)
                                        if response_send_file.status_code == 201 or response_send_file.status_code == 200:
                                            _logger.info("\nSend file attachment successfully11")
                        else:
                            no_phone_partners.append(res_partner_id.name)
                    else:
                        raise UserError(_('Please enter %s mobile number or select country', res_partner_id.name))
                if len(no_phone_partners) >= 1:
                    raise UserError(_('Please add valid whatsapp number for %s customer') % ', '.join(no_phone_partners))
        else:
            raise UserError(_('Please authorize your mobile number with chat api'))


class SendWAMessageSendResPartner(models.TransientModel):
    _name = 'whatsapp.msg.send.partner'
    _description = 'Send WhatsApp Message'

    def _default_unique_user(self):
        IPC = self.env['ir.config_parameter'].sudo()
        dbuuid = IPC.get_param('database.uuid')
        return dbuuid + '_' + str(self.env.uid)

    partner_ids = fields.Many2many('res.partner', 'whatsapp_msg_send_partner_res_partner_rel', 'wizard_id', 'partner_id', 'Recipients')
    message = fields.Text('Message', required=True)
    attachment_ids = fields.Many2many('ir.attachment', 'whatsapp_msg_send_partner_ir_attachments_rel', 'wizard_id', 'attachment_id', 'Attachments')
    unique_user = fields.Char(default=_default_unique_user)

    def _phone_get_country(self, partner):
        if 'country_id' in partner:
            return partner.country_id
        return self.env.user.company_id.country_id

    def _msg_sanitization(self, partner, field_name):
        number = partner[field_name]
        if number and _sms_phonenumbers_lib_imported:
            country = self._phone_get_country(partner)
            country_code = country.code if country else None
            try:
                phone_nbr = phonenumbers.parse(number, region=country_code, keep_raw_input=True)
            except phonenumbers.phonenumberutil.NumberParseException:
                return number
            if not phonenumbers.is_possible_number(phone_nbr) or not phonenumbers.is_valid_number(phone_nbr):
                return number
            phone_fmt = phonenumbers.PhoneNumberFormat.E164
            return phonenumbers.format_number(phone_nbr, phone_fmt)
        else:
            return number

    def _get_records(self, model):
        if self.env.context.get('active_domain'):
            records = model.search(self.env.context.get('active_domain'))
        elif self.env.context.get('active_ids'):
            records = model.browse(self.env.context.get('active_ids', []))
        else:
            records = model.browse(self.env.context.get('active_id', []))
        return records

    @api.model
    def default_get(self, fields):
        result = super(SendWAMessageSendResPartner, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        res_id = self.env.context.get('active_id')
        if res_id:
            rec = self.env[active_model].browse(res_id)
            Attachment = self.env['ir.attachment']
            res_name = 'Invoice_' + rec.number.replace('/', '_') if active_model == 'account.move' else rec.name.replace('/', '_')
            msg = result.get('message', '')
            result['message'] = msg

            if not self.env.context.get('default_recipients') and active_model and hasattr(self.env[active_model], '_sms_get_default_partners'):
                model = self.env[active_model]
                records = self._get_records(model)
                partners = records._sms_get_default_partners()
                phone_numbers = []
                no_phone_partners = []
                if active_model != 'res.partner':
                    is_attachment_exists = Attachment.search([('res_id', '=', res_id), ('name', 'like', res_name + '%'), ('res_model', '=', active_model)], limit=1)
                    if not is_attachment_exists:
                        attachments = []
                        if active_model == 'sale.order':
                            template = self.env.ref('sale.email_template_edi_sale')
                        elif active_model == 'account.move':
                            template = self.env.ref('account.email_template_edi_invoice')
                        elif active_model == 'purchase.order':
                            if self.env.context.get('send_rfq', False):
                                template = self.env.ref('purchase.email_template_edi_purchase')
                            else:
                                template = self.env.ref('purchase.email_template_edi_purchase_done')
                        elif active_model == 'stock.picking':
                            template = self.env.ref('stock.mail_template_data_delivery_confirmation')
                        elif active_model == 'account.payment':
                            template = self.env.ref('account.mail_template_data_payment_receipt')
                        report = template.report_template
                        report_service = report.report_name
                        if report.report_type not in ['qweb-html', 'qweb-pdf']:
                            raise UserError(_('Unsupported report type %s found.') % report.report_type)
                        res, format = report._render_qweb_pdf([res_id])
                        res = base64.b64encode(res)
                        if not res_name:
                            res_name = 'report.' + report_service
                        ext = "." + format
                        if not res_name.endswith(ext):
                            res_name += ext
                        attachments.append((res_name, res))
                        attachment_ids = []
                        for attachment in attachments:
                            attachment_data = {
                                'name': attachment[0],
                                'datas': attachment[1],
                                'type': 'binary',
                                'res_model': active_model,
                                'res_id': res_id,
                            }
                            attachment_ids.append(Attachment.create(attachment_data).id)
                        if attachment_ids:
                            result['attachment_ids'] = [(6, 0, attachment_ids)]
                    else:
                        result['attachment_ids'] = [(6, 0, [is_attachment_exists.id])]

                for partner in partners:
                    number = self._msg_sanitization(partner, self.env.context.get('field_name') or 'mobile')
                    if number:
                        phone_numbers.append(number)
                    else:
                        no_phone_partners.append(partner.name)
                if len(partners) > 1:
                    if no_phone_partners:
                        raise UserError(_('Missing mobile number for %s.') % ', '.join(no_phone_partners))
                result['partner_ids'] = [(6, 0, partners.ids)]
                result['message'] = msg
        return result

    def action_send_msg_res_partner(self):
        Param = self.env['res.config.settings'].sudo().get_values()
        active_id = self.partner_ids
        active_model = 'res.partner'
        phone_numbers = []
        no_phone_partners = []
        try:
            status_url = Param.get('whatsapp_endpoint') + '/status?token=' + Param.get('whatsapp_token')
            status_response = requests.get(status_url)
        except Exception as e_log:
            _logger.exception(e_log)
            raise UserError(_('Please add proper whatsapp endpoint or whatsapp token'))
        json_response_status = json.loads(status_response.text)
        if (status_response.status_code == 200 or status_response.status_code == 201) and json_response_status['accountStatus'] == 'authenticated':
            if active_model == 'res.partner':
                for res_partner_id in self.partner_ids:
                    number = str(res_partner_id.country_id.phone_code) + res_partner_id.mobile
                    if res_partner_id.country_id.phone_code and res_partner_id.mobile:
                        whatsapp_number = res_partner_id.mobile
                        whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
                        whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(res_partner_id.country_id.phone_code), "")
                        phone_exists_url = Param.get('whatsapp_endpoint') + '/checkPhone?token=' + Param.get(
                            'whatsapp_token') + '&phone=' + str(
                            res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                        phone_exists_response = requests.get(phone_exists_url)
                        json_response_phone_exists = json.loads(phone_exists_response.text)
                        if (phone_exists_response.status_code == 200 or phone_exists_response.status_code == 201) and json_response_phone_exists['result'] == 'exists':
                            url = Param.get('whatsapp_endpoint') + '/sendMessage?token=' + Param.get('whatsapp_token')
                            headers = {"Content-Type": "application/json"}
                            tmp_dict = {
                                "phone": "+" + str(res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                "body": self.message}
                            response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                            if response.status_code == 201 or response.status_code == 200:
                                _logger.info("\nSend Message successfully")
                            if self.attachment_ids:
                                for attachment in self.attachment_ids:
                                    with open("/tmp/" + attachment.name, 'wb') as tmp:
                                        encoded_file = str(attachment.datas)
                                        url_send_file = Param.get('whatsapp_endpoint') + '/sendFile?token=' + Param.get('whatsapp_token')
                                        headers_send_file = {"Content-Type": "application/json"}
                                        dict_send_file = {
                                            "phone": "+" + str(res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                            "body": "data:" + attachment.mimetype + ";base64," + encoded_file[2:-1],
                                            "filename": attachment.name
                                        }
                                        response_send_file = requests.post(url_send_file, json.dumps(dict_send_file), headers=headers_send_file)
                                        if response_send_file.status_code == 201 or response_send_file.status_code == 200:
                                            _logger.info("\nSend file attachment successfully11")
                        else:
                            no_phone_partners.append(res_partner_id.name)
                    else:
                        raise UserError(_('Please enter %s mobile number or select country', res_partner_id))
                if len(no_phone_partners) >= 1:
                    raise UserError(
                        _('Please add valid whatsapp number for %s customer') % ', '.join(no_phone_partners))
        else:
            raise UserError(_('Please authorize your mobile number with chat api'))


class SendWAMessage(models.TransientModel):
    _name = 'whatsapp.msg'
    _description = 'Send WhatsApp Message'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_unique_user(self):
        IPC = self.env['ir.config_parameter'].sudo()
        dbuuid = IPC.get_param('database.uuid')
        return dbuuid + '_' + str(self.env.uid)

    partner_ids = fields.Many2many('res.partner', 'whatsapp_msg_res_partner_rel', 'wizard_id', 'partner_id', 'Recipients')
    message = fields.Text('Message', required=True)
    attachment_ids = fields.Many2many('ir.attachment', 'whatsapp_msg_ir_attachments_rel', 'wizard_id', 'attachment_id', 'Attachments', tracking=True)
    unique_user = fields.Char(default=_default_unique_user)

    def format_amount(self, amount, currency):
        fmt = "%.{0}f".format(currency.decimal_places)
        lang = self.env['res.lang']._lang_get(self.env.context.get('lang') or 'en_US')
        formatted_amount = lang.format(fmt, currency.round(amount), grouping=True, monetary=True) \
            .replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'-\N{ZERO WIDTH NO-BREAK SPACE}')
        pre = post = u''
        if currency.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=currency.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=currency.symbol or '')
        return u'{pre}{0}{post}'.format(formatted_amount, pre=pre, post=post)

    def _phone_get_country(self, partner):
        if 'country_id' in partner:
            return partner.country_id
        return self.env.user.company_id.country_id

    def _msg_sanitization(self, partner, field_name):
        number = partner[field_name]
        if number and _sms_phonenumbers_lib_imported:
            country = self._phone_get_country(partner)
            country_code = country.code if country else None
            try:
                phone_nbr = phonenumbers.parse(number, region=country_code, keep_raw_input=True)
            except phonenumbers.phonenumberutil.NumberParseException:
                return number
            if not phonenumbers.is_possible_number(phone_nbr) or not phonenumbers.is_valid_number(phone_nbr):
                return number
            phone_fmt = phonenumbers.PhoneNumberFormat.E164
            return phonenumbers.format_number(phone_nbr, phone_fmt)
        else:
            return number

    def _get_records(self, model):
        if self.env.context.get('active_domain'):
            records = model.search(self.env.context.get('active_domain'))
        elif self.env.context.get('active_ids'):
            records = model.browse(self.env.context.get('active_ids', []))
        else:
            records = model.browse(self.env.context.get('active_id', []))
        return records

    def cleanhtml(self, raw_html):
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext

    @api.model
    def default_get(self, fields):
        result = super(SendWAMessage, self).default_get(fields)
        active_model = self.env.context.get('active_model')
        res_id = self.env.context.get('active_id')
        rec = self.env[active_model].browse(res_id)
        rec = rec.with_context(lang=rec.partner_id.lang)
        self = self.with_context(lang=rec.partner_id.lang)
        Attachment = self.env['ir.attachment']
        res_name = ''
        if active_model == 'account.move':
            if rec.name:
                res_name = 'Invoice_' + rec.name.replace('/', '_') if active_model == 'account.move' else rec.name.replace('/', '_')
        msg = result.get('message', '')
        result['message'] = msg
        res_user_id = self.env['res.users'].search([('partner_id', '=', rec.partner_id.id)])
        if not self.env.context.get('default_recipients') and active_model and hasattr(self.env[active_model], '_sms_get_default_partners'):
            model = self.env[active_model]
            records = self._get_records(model)
            partners = records._sms_get_default_partners()
            phone_numbers = []
            no_phone_partners = []
            self = self.with_context(lang=rec.partner_id.lang)
            if active_model == 'sale.order':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    # doc_name = 'quotation' if rec.state in ('approved', 'to_confirm') else 'order'
                    doc_name = _("order")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_order_info_msg'):
                        msg += "\n\n " + _("Your") + " "
                        if self.env.context.get('proforma'):
                            msg += _("in attachment your pro-forma invoice")
                        else:
                            msg += doc_name + " *" + rec.name + "* "
                        if rec.origin:
                            msg += _("(with reference") + " : " + rec.origin + ")"
                        msg += _(" is placed")
                        msg += "\n" + _("Total Amount") + ": " + self.format_amount(rec.amount_total, rec.pricelist_id.currency_id)
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_order_product_details_msg'):
                        msg += "\n\n" + _("Following is your order details.")
                        for line_id in rec.order_line:
                            if line_id:
                                if line_id.product_id:
                                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.display_name
                                if line_id.product_uom_qty and line_id.product_uom.name:
                                    msg += "\n*" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                                if line_id.price_unit:
                                    msg += "\n*" + _("Unit Price") + ":* " + str(line_id.price_unit)
                                if line_id.price_subtotal:
                                    msg += "\n*" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                            msg += "\n------------------"
                    msg += "\n" + _("Please find attached sale order which will help you to get detailed information.")
                    # if rec
                    if res_user_id.has_group('pragmatic_odoo_whatsapp_integration.group_enable_signature'):
                        user_signature = self.cleanhtml(res_user_id.signature)
                        msg += "\n\n" + user_signature

                    report_obj = self.env.ref('sale.action_report_saleorder')
                    pdf = report_obj.sudo()._render_qweb_pdf([rec.id])
                    extension = 'pdf'
                    report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                    filename = "%s.%s" % (report_name, extension)
                    res = base64.b64encode(pdf[0])
                    attachments = []
                    attachments.append((filename, pdf))
                    attachment_ids = []

                    attachment_data = {
                        'name': filename,
                        'datas': res,
                        'type': 'binary',
                        'res_model': 'sale.order',
                        'res_id': rec.id,
                    }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))

            if active_model == 'account.move':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    doc_name = _("invoice")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_invoice_info_msg'):
                        msg += "\n\n" + _("Here is your ")
                        if rec.state == 'draft':
                            msg += doc_name + " *" + _("draft invoice") + "* "
                        else:
                            msg += doc_name + " *" + rec.name + "* "
                        msg += "\n" + _("Total Amount") + ": " + self.format_amount(rec.amount_total, rec.currency_id)
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_invoice_product_details_msg'):
                        msg += "\n\n" + _("Following is your order details.")
                        for line_id in rec.invoice_line_ids:
                            if line_id:
                                if line_id.product_id:
                                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.display_name
                                if line_id.quantity:
                                    msg += "\n*" + _("Qty") + ":* " + str(line_id.quantity)
                                if line_id.price_unit:
                                    msg += "\n*" + _("Unit Price") + ":* " + str(line_id.price_unit)
                                if line_id.price_subtotal:
                                    msg += "\n*" + _("Subtotal") + ":* " + str(line_id.price_subtotal)
                            msg += "\n------------------"

                    msg += "\n" + _("Please find attached invoice which will help you to get detailed information.")
                    if res_user_id.has_group('pragmatic_odoo_whatsapp_integration.group_invoice_enable_signature'):
                        user_signature = self.cleanhtml(res_user_id.signature)
                        msg += "\n\n" + user_signature
                    report_obj = self.env.ref('account.account_invoices_without_payment')
                    pdf = report_obj.sudo()._render_qweb_pdf([rec.id])
                    extension = 'pdf'
                    report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                    filename = "%s.%s" % (report_name, extension)
                    res = base64.b64encode(pdf[0])
                    attachments = []
                    attachments.append((filename, pdf))
                    attachment_ids = []

                    attachment_data = {
                        'name': filename,
                        'datas': res,
                        'type': 'binary',
                        'res_model': 'account.move',
                        'res_id': rec.id,
                    }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))

            if active_model == 'stock.picking':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    # doc_name = 'stock picking' if rec.state in ('assigned', 'done') else 'picking'
                    doc_name = _("Delivery order")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_stock_info_msg'):
                        msg += "\n\n" + _("Here is your") + " "
                        msg += doc_name + " *" + rec.name + "* "
                        if rec.origin:
                            msg += "(" + _("with reference") + ": " + rec.origin + ")"
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_stock_product_details_msg'):
                        msg += "\n\n" + _("Following is your delivery order details.")
                        for line_id in rec.move_ids_without_package:
                            if line_id:
                                if line_id.product_id:
                                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.display_name
                                if line_id.product_uom_qty and line_id.product_uom:
                                    msg += "\n*" + _("Qty") + ":* " + str(line_id.product_uom_qty) + " " + str(line_id.product_uom.name)
                                # if line_id.quantity_done:
                                #     msg += "\n*" + _("Done") + ":* "+str(line_id.quantity_done)
                            msg += "\n------------------"
                    msg += "\n" + _("Please find attached delivery order which will help you to get detailed information.")
                    if res_user_id.has_group('pragmatic_odoo_whatsapp_integration.group_stock_enable_signature'):
                        user_signature = self.cleanhtml(res_user_id.signature)
                        msg += "\n\n" + user_signature

                    report_obj = self.env.ref('stock.action_report_picking')
                    pdf = report_obj.sudo()._render_qweb_pdf([rec.id])
                    extension = 'pdf'
                    report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                    filename = "%s.%s" % (report_name, extension)
                    res = base64.b64encode(pdf[0])
                    attachments = []
                    attachments.append((filename, pdf))
                    attachment_ids = []

                    attachment_data = {
                        'name': filename,
                        'datas': res,
                        'type': 'binary',
                        'res_model': 'stock.picking',
                        'res_id': rec.id,
                    }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))

            if active_model == 'purchase.order':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    doc_name = _("Purchase order")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_purchase_order_info_msg'):
                        msg += "\n\n" + _("Here is your") + " "
                        msg += doc_name + " *" + rec.name + "* "
                        if rec.origin:
                            msg += "(" + _("with reference") + ": " + rec.origin + ")"
                        msg += "\n" + _("Total Amount") + ": " + self.format_amount(rec.amount_total, rec.currency_id) + "."
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_purchase_order_product_details_msg'):
                        msg += "\n\n" + _("Following is your order details.")
                        for line_id in rec.order_line:
                            if line_id:
                                if line_id.product_id:
                                    msg += "\n\n*" + _("Product") + ":* " + line_id.product_id.display_name
                                if line_id.product_qty and line_id.product_uom:
                                    msg += "\n*" + _("Qty") + ":* " + str(line_id.product_qty) + " " + str(line_id.product_uom.name)
                                if line_id.price_unit:
                                    msg += "\n*" + _("Unit Price") + ":* " + str(line_id.price_unit)
                                if line_id.price_subtotal:
                                    msg += "\n*" + _("Subtotal") + ":* " + str(line_id.price_subtotal)

                            msg += "\n------------------"
                    msg += "\n " + _("Please find attached purchase order which will help you to get detailed information.")
                    if res_user_id.has_group('pragmatic_odoo_whatsapp_integration.group_purchase_enable_signature'):
                        user_signature = self.cleanhtml(res_user_id.signature)
                        msg += "\n\n" + user_signature


                    report_obj = self.env.ref('purchase.action_report_purchase_order')
                    pdf = report_obj.sudo()._render_qweb_pdf([rec.id])
                    extension = 'pdf'
                    report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                    filename = "%s.%s" % (report_name, extension)
                    res = base64.b64encode(pdf[0])
                    attachments = []
                    attachments.append((filename, pdf))
                    attachment_ids = []

                    attachment_data = {
                        'name': filename,
                        'datas': res,
                        'type': 'binary',
                        'res_model': 'purchase.order',
                        'res_id': rec.id,
                    }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))

            if active_model == 'account.payment':
                if rec.partner_id.mobile and rec.partner_id.country_id.phone_code:
                    doc_name = _("account payment")
                    res_user_id = self.env['res.users'].search([('id', '=', self.env.user.id)])
                    msg = _("Hello") + " " + rec.partner_id.name
                    if rec.partner_id.parent_id:
                        msg += "(" + rec.partner_id.parent_id.name + ")"
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_invoice_info_msg'):
                        msg += "\n\n" + _("Your") + " "
                        if rec.name:
                            msg += doc_name + " *" + rec.name + "* "
                        else:
                            msg += doc_name + " *" + _("Draft Payment") + "* "
                        msg += " " + _("with Total Amount") + " " + self.format_amount(rec.amount, rec.currency_id) + "."
                    if self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_invoice_product_details_msg'):
                        msg += "\n\n" + _("Following is your payment details.")
                        if rec:
                            if rec.payment_type:
                                msg += "\n\n*" + _("Payment Type") + ":* " + rec.payment_type
                            if rec.journal_id:
                                msg += "\n*" + _("Payment Journal") + ":* " + rec.journal_id.name
                            if rec.date:
                                msg += "\n*" + _("Payment date") + ":* " + str(rec.date)
                            if rec.ref:
                                msg += "\n*" + _("Memo") + ":* " + str(rec.ref)
                    msg += "\n " + _("Please find attached account payment which will help you to get detailed information.")
                    if res_user_id.has_group('pragmatic_odoo_whatsapp_integration.group_invoice_enable_signature'):
                        user_signature = self.cleanhtml(res_user_id.signature)
                        msg += "\n\n" + user_signature
                    attachment_ids = []
                    attachment_data = {}
                    # if rec.state == 'draft':


                    report_obj = self.env.ref('account.action_report_payment_receipt')
                    pdf = report_obj.sudo()._render_qweb_pdf([rec.id])
                    extension = 'pdf'
                    if report_obj.print_report_name:
                        report_name = safe_eval(report_obj.print_report_name, {'object': rec, 'time': time})
                        filename = "%s.%s" % (report_name, extension)
                        res = base64.b64encode(pdf[0])
                        attachments = []
                        attachments.append((filename, pdf))
                        attachment_ids = []

                        attachment_data = {
                            'name': filename,
                            'datas': res,
                            'type': 'binary',
                            'res_model': 'account.payment',
                            'res_id': rec.id,
                        }
                    else:
                        pdf = self.env.ref('account.action_report_payment_receipt').sudo()._render_qweb_pdf([rec.id])
                        res = base64.b64encode(pdf[0])
                        res_name = 'account.action_report_payment_receipt'
                        attachments = []
                        attachments.append((res_name, pdf))
                        attachment_ids = []
                        attachment_data = {
                            'name': 'Payment Receipt.pdf',
                            'datas': res,
                            'type': 'binary',
                            'res_model': 'account.payment',
                            'res_id': rec.id,
                        }
                    attachment_ids.append(Attachment.create(attachment_data).id)
                    if attachment_ids:
                        result['attachment_ids'] = [(6, 0, attachment_ids)]
                else:
                    raise UserError(_('Please enter mobile number or select country'))
            result['message'] = msg
            for partner in partners:
                number = self._msg_sanitization(partner, self.env.context.get('field_name') or 'mobile')
                if number:
                    phone_numbers.append(number)
                else:
                    no_phone_partners.append(partner.name)
            if len(partners) > 1:
                if no_phone_partners:
                    raise UserError(_('Missing mobile number for %s.') % ', '.join(no_phone_partners))
            result['partner_ids'] = [(6, 0, partners.ids)]
            result['message'] = msg
        return result

    def convert_to_html(self, message):
        for data in re.findall(r'\*.*?\*', message):
            message = message.replace(data, "<strong>" + data.strip('*') + "</strong>")
        return message

    def action_send_msg(self):
        Param = self.env['res.config.settings'].sudo().get_values()
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        try:
            status_url = Param.get('whatsapp_endpoint') + '/status?token=' + Param.get('whatsapp_token')
            status_response = requests.get(status_url)
        except Exception as e_log:
            _logger.exception(e_log)
            raise UserError(_('Please add proper whatsapp endpoint or whatsapp token'))
        json_response_status = json.loads(status_response.text)
        if (status_response.status_code == 200 or status_response.status_code == 201) and json_response_status['accountStatus'] == 'authenticated':
            if active_model == 'res.partner':
                for res_partner_id in self.partner_ids:
                    whatsapp_number = res_partner_id.mobile
                    whatsapp_msg_number_without_space = whatsapp_number.replace(" ", "")
                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(res_partner_id.country_id.phone_code), "")
                    number = str(res_partner_id.country_id.phone_code) + res_partner_id.mobile
                    if res_partner_id.country_id.phone_code and res_partner_id.mobile:
                        phone_exists_url = Param.get('whatsapp_endpoint') + '/checkPhone?token=' + Param.get(
                            'whatsapp_token') + '&phone=' + str(
                            res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                        phone_exists_response = requests.get(phone_exists_url)
                        json_response_phone_exists = json.loads(phone_exists_response.text)
                        if (phone_exists_response.status_code == 200 or phone_exists_response.status_code == 201) and json_response_phone_exists['result'] == 'exists':
                            url = Param.get('whatsapp_endpoint') + '/sendMessage?token=' + Param.get('whatsapp_token')
                            headers = {"Content-Type": "application/json"}
                            tmp_dict = {
                                "phone": "+" + str(res_partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                "body": self.message}
                            response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                            if response.status_code == 201 or response.status_code == 200:
                                _logger.info("\nSend Message successfully")

            elif active_model == 'sale.order' or active_model == 'account.move' or active_model == 'purchase.order' or active_model == 'stock.picking' or active_model == \
                    'account.payment':
                rec = self.env[active_model].browse(active_id)
                number = str(rec.partner_id.country_id.phone_code) + rec.partner_id.mobile
                comment = "fa fa-whatsapp"
                dict_send_file = {}
                # body_html = tools.append_content_to_html(
                #     '<div class = "%s"></div>' % tools.ustr(comment), self.message)
                mail_message_body = ''
                mail_message_body = """<p style='margin:0px; font-size:13px; font-family:"Lucida Grande", Helvetica, Verdana, Arial, sans-serif'><img src="/web_editor/font_to_img/62002/rgb(73,80,87)/13" data-class="fa fa-whatsapp" style="border-style:none; vertical-align:middle; height:auto; width:auto" width="0" height="0"></p>"""
                mail_message_body +=  self.message
                update_msg = self.convert_to_html(mail_message_body)
                body_mail_msg = "<br />".join(update_msg.split("\n"))
                whatsapp_msg_number = rec.partner_id.mobile
                whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "");
                whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(
                    '+' + str(rec.partner_id.country_id.phone_code), "")
                if rec.partner_id.country_id.phone_code and rec.partner_id.mobile:
                    phone_exists_url = Param.get('whatsapp_endpoint') + '/checkPhone?token=' + Param.get(
                        'whatsapp_token') + '&phone=' + str(
                        rec.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code
                    phone_exists_response = requests.get(phone_exists_url)
                    json_response_phone_exists = json.loads(phone_exists_response.text)
                    if (phone_exists_response.status_code == 200 or phone_exists_response.status_code == 201) and json_response_phone_exists['result'] == 'exists':
                        url = Param.get('whatsapp_endpoint') + '/sendMessage?token=' + Param.get('whatsapp_token')
                        headers = {"Content-Type": "application/json"}
                        tmp_dict = {
                            "phone": "+" + str(rec.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                            "body": self.message}
                        response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                        if response.status_code == 201 or response.status_code == 200:
                            _logger.info("\nSend Message successfully")
                        dict_send_file = {}
                        if self.attachment_ids:
                            url_send_file = Param.get('whatsapp_endpoint') + '/sendFile?token=' + Param.get('whatsapp_token')
                            headers_send_file = {"Content-Type": "application/json"}
                            whatsapp_msg_number = rec.partner_id.mobile
                            whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "")
                            whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(rec.partner_id.country_id.phone_code), "")
                            for attachment in self.attachment_ids:
                                encoded_file = str(attachment.datas)
                                if attachment.mimetype:
                                    dict_send_file = {
                                        "phone": "+" + str(rec.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                                        "body": "data:" + attachment.mimetype + ";base64," + encoded_file[2:-1],
                                        "filename": attachment.name
                                    }
                                    response_send_file = requests.post(url_send_file, json.dumps(dict_send_file), headers=headers_send_file)
                                    if response_send_file.status_code == 201 or response_send_file.status_code == 200:
                                        _logger.info("\nSend file attachment successfully")
                            mail_message_obj = self.env['mail.message']
                            if active_model == 'sale.order' and self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_display_chatter_message'):
                                # rec.access_token = str(uuid.uuid4())
                                mail_message_id = mail_message_obj.sudo().create({
                                    'res_id': rec.id,
                                    'model': active_model,
                                    'body': body_mail_msg,
                                    'attachment_ids': [(4, attachment.id) for attachment in self.attachment_ids],
                                })
                                mail_message_id.message_format()
                            if active_model == 'purchase.order' and self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_purchase_display_chatter_message'):
                                # rec.access_token = str(uuid.uuid4())
                                mail_message_id = mail_message_obj.sudo().create({
                                    'res_id': rec.id,
                                    'model': active_model,
                                    'body': body_mail_msg,
                                    'attachment_ids': [(4, attachment.id) for attachment in
                                                       self.attachment_ids],

                                })
                                mail_message_id.message_format()
                            if active_model == 'stock.picking' and self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_stock_display_chatter_message'):
                                # rec.access_token = str(uuid.uuid4())
                                mail_message_id = mail_message_obj.sudo().create({
                                    'res_id': rec.id,
                                    'model': active_model,
                                    'body': body_mail_msg,
                                    'attachment_ids': [(4, attachment.id) for attachment in
                                                       self.attachment_ids],

                                })
                                mail_message_id.message_format()
                            if (active_model == 'account.move' or active_model == 'account.payment') and self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_invoice_display_chatter_message'):
                                # rec.access_token = str(uuid.uuid4())
                                mail_message_id = mail_message_obj.sudo().create({
                                    'res_id': rec.id,
                                    'model': active_model,
                                    'body': body_mail_msg,
                                    'attachment_ids': [(4, attachment.id) for attachment in
                                                       self.attachment_ids],

                                })
                                mail_message_id.message_format()

                        elif not self.attachment_ids and response.status_code == 201 or response.status_code == 200:
                            if active_model == 'sale.order' and self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_display_chatter_message'):
                                mail_message_id = self.env['mail.message'].sudo().create({
                                    'res_id': rec.id,
                                    'model': active_model,
                                    'body': body_mail_msg
                                })
                                mail_message_id.message_format()

                            if active_model == 'purchase.order' and self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_purchase_display_chatter_message'):
                                mail_message_id = self.env['mail.message'].sudo().create({
                                    'res_id': rec.id,
                                    'model': active_model,
                                    'body': body_mail_msg
                                })
                                mail_message_id.message_format()

                            if active_model == 'stock.picking' and self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_stock_display_chatter_message'):
                                mail_message_id = self.env['mail.message'].sudo().create({
                                    'res_id': rec.id,
                                    'model': active_model,
                                    'body': body_mail_msg
                                })
                                mail_message_id.message_format()

                            if (active_model == 'account.move' or active_model == 'account.payment') and self.env['ir.config_parameter'].sudo().get_param('pragmatic_odoo_whatsapp_integration.group_invoice_display_chatter_message'):
                                mail_message_id = self.env['mail.message'].sudo().create({
                                    'res_id': rec.id,
                                    'model': active_model,
                                    'body': body_mail_msg
                                })
                                mail_message_id.message_format()
                    else:
                        raise UserError(_('Please add valid whatsapp number for %s customer') % rec.partner_id.name)
                else:
                    raise UserError(_('Please enter %s mobile number or select country', rec.partner_id))
        else:
            raise UserError(_('Please authorize your mobile number with chat api'))


class RetryWAMsg(models.TransientModel):
    _name = 'whatsapp.retry.msg'
    _description = 'Retry WhatsApp Message'

    name = fields.Char()

    def action_retry_send_msg(self):
        res_id = self.env.context.get('wiz_id')
        if res_id:
            time.sleep(5)
            self.env['whatsapp.msg.res.partner'].browse(res_id).action_send_msg()
        return True
