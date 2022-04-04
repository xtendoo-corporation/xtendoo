import logging
from odoo import api, fields, models, _
import requests
import json

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    mobile = fields.Char()
    country_id = fields.Many2one('res.country', 'Country')

    @api.model
    def signup(self, values, token=None):
        values.update({'email': values.get('email') or values.get('login')})
        if token:
            # signup with a token: find the corresponding partner id
            partner = self.env['res.partner']._signup_retrieve_partner(token, check_validity=True, raise_exception=True)
            # invalidate signup token
            partner.write({'signup_token': False, 'signup_type': False, 'signup_expiration': False})
            partner_user = partner.user_ids and partner.user_ids[0] or False
            # avoid overwriting existing (presumably correct) values with geolocation data
            if partner.country_id or partner.zip or partner.city:
                values.pop('city', None)
                values.pop('country_id', None)
            if partner.lang:
                values.pop('lang', None)
            if partner_user:
                # user exists, modify it according to values
                values.pop('login', None)
                values.pop('name', None)
                partner_user.write(values)
                if not partner_user.login_date:
                    partner_user._notify_inviter()
                return (self.env.cr.dbname, partner_user.login, values.get('password'))
            else:
                # user does not exist: sign up invited user
                values.update({
                    'name': partner.name,
                    'partner_id': partner.id,
                    'email': values.get('email') or values.get('login'),
                })
                if partner.company_id:
                    values['company_id'] = partner.company_id.id
                    values['company_ids'] = [(6, 0, [partner.company_id.id])]
                partner_user = self._signup_create_user(values)
                partner_user._notify_inviter()

        else:
            values['mobile'] = values.get('mobile')
            values['country_id'] = values.get('country_id')
            user_id = self._signup_create_user(values)
            if values['mobile']:
                user_id.partner_id.mobile = values['mobile']
            if values['country_id']:
                user_id.partner_id.country_id = int(values['country_id'])
            Param = self.env['res.config.settings'].sudo().get_values()
            if values.get('country_id'):
                country_id = self.env['res.country'].sudo().search([('id', '=', values.get('country_id'))])
                msg = ''
                try:
                    if values.get('mobile') and country_id:
                        whatsapp_number = "+" + str(country_id.phone_code) + "" + values.get('mobile')
                        url = Param.get('whatsapp_endpoint') + '/sendMessage?token=' + Param.get('whatsapp_token')
                        headers = { "Content-Type": "application/json" }
                        tmp_dict = {
                            "phone": "+" + whatsapp_number,
                            "body": _("Hello ") + values.get('name') + ',' + "\n" +_("You have successfully registered and logged in") + "\n"+_("*Your Email:* ") + " "+values.get('login'),
                        }
                        response = requests.post(url, json.dumps(tmp_dict), headers=headers)
                        if response.status_code == 201 or response.status_code == 200:
                            _logger.info("\nSend Message successfully")
                except Exception as e_log:
                    _logger.exception("Exception in send message to user %s:\n", str(e_log))
        return (self.env.cr.dbname, values.get('login'), values.get('password'))
