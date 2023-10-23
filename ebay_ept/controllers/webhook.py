#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import hashlib
import json
import urllib.parse as urlparse
from urllib.parse import parse_qs
import logging
from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class Webhook(http.Controller):
    _endpoint = '/ebay_partners_delete'

    @http.route(_endpoint, type='http', auth="public", methods=['GET'], csrf=False)
    def get_challenge_code_for_check_validations(self, **kwargs):
        """
        This controller is call when we configure endpoint in the eBay Developer Account
        for "Marketplace Account Deletion/Closure Notifications".
        Receive Parameter : Get Challenge Code as a querystring parameter with Endpoint url.
        :return : Return challengeResponse to eBay with status code 200 OK and json content type.

        @author: Harsh Parekh @Emipro Technologies Pvt. Ltd on date 21/07/2021.
        Task Id : 175703
        """
        browser_url = request.httprequest.url
        if "challenge_code" in browser_url:
            parsed = urlparse.urlparse(browser_url)
            challange_code = parse_qs(parsed.query)['challenge_code'][0]
            config_para = request.env['ir.config_parameter'].sudo()
            verification_token = config_para.get_param('ebay_ept.ebay_deletion_token_ept')
            end_point = config_para.get_param('web.base.url') + "/ebay_partners_delete"
            prepare_hashlib_data = hashlib.sha256(challange_code.encode() +
                                                  verification_token.encode() +
                                                  end_point.encode())
            hashlib_data = prepare_hashlib_data.hexdigest()
            challengeresponse = {"challengeResponse": hashlib_data,
                                 "status": "200 OK", 'content-type': 'application/json'}
            return json.dumps(challengeresponse)

    @http.route(_endpoint, type='json', auth="public", methods=['POST'], csrf=False)
    def update_partner_informations_ept(self, **kwargs):
        """
        When any user account delete from eBay then if configured endpoint there then
        it will call this controller in odoo and this controller call 'update_partner_informations' method
        for update the partner information with response.

        @author: Harsh Parekh @Emipro Technologies Pvt. Ltd on date 21/07/2021.
        Task Id : 175703
        """
        response_data = json.loads(request.httprequest.data.decode('utf-8')) if request else {}
        if response_data:
            self.update_partner_informations(response_data)
        return True

    def update_partner_informations(self, response_data):
        """
        This method blank partner all the mentioned details based on eBay response.
        it will search partner based on userId and if found partner then blank details
        and post that related message in partner model with reason.

        @author: Harsh Parekh @Emipro Technologies Pvt. Ltd on date 21/07/2021.
        Task Id : 175703
        """
        partner_obj = request.env['res.partner']
        user_id = response_data.get("notification", {}).get("data", {}).get("userId", "")
        exist_partner = partner_obj.sudo().search([('ebay_user_id', '=ilike', user_id)])
        if exist_partner:
            exist_partner.sudo().write(
                {"name": "eBay", "street": " ", "street2": " ",
                 "city": " ", "state_id": False, "country_id": False, "zip": " ",
                 "phone": " ", "email": " ", "ebay_user_id": " ", "ebay_user_email_id": " "})

            message = "This Partner informations like name, street, street2, " \
                      "city, state, country, zip, phone, email, EBay User ID, EBay User Email" \
                      " values are blank due to account is delete from eBay that reason."

            exist_partner.sudo().message_post(body=_(message))
        return True
