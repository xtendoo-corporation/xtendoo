# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _
from odoo.exceptions import UserError


class WooResPartnerEpt(models.Model):
    _name = "woo.res.partner.ept"
    _description = "WooCommerce Res Partner"

    partner_id = fields.Many2one("res.partner", "Customer", ondelete='cascade')
    woo_customer_id = fields.Char(help="WooCommerce customer id.")
    woo_instance_id = fields.Many2one("woo.instance.ept", "WooCommerce Instances",
                                      help="Instance id managed for identified that customer associated with which "
                                           "instance.")

    def find_woo_customer(self, woo_instance, customer_id):
        partner_obj = self.env['res.partner']
        partner = False
        address_key_list = ['name', 'street', 'street2', 'city', 'zip', 'phone', 'state_id', 'country_id']
        wc_api = woo_instance.woo_connect()
        try:
            response = wc_api.get('customers/%s' % customer_id)
        except Exception as error:
            raise UserError(_("Something went wrong while importing Customers.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))

        data = response.json()
        if data:
            bill_data = data.get('billing')
            partner_type = 'delivery'
            parent_id = partner_obj.search_partner_by_email(data.get('email'))
            email = data.get("email", False)
            first_name = data.get("first_name")
            last_name = data.get("last_name")
            name = "%s %s" % (first_name, last_name)
            phone = data.get("phone")
            address1 = bill_data.get('address_1')
            address2 = bill_data.get('address_2')
            city = bill_data.get('city')
            zipcode = bill_data.get("postcode")
            state_code = bill_data.get("state")
            country_code = bill_data.get("country")

            country = partner_obj.get_country(country_code)
            state = partner_obj.create_or_update_state_ept(country_code, state_code, False, country)

            partner_vals = {
                'email': email or False, 'name': name, 'phone': phone,
                'street': address1, 'street2': address2, 'city': city, 'zip': zipcode,
                'state_id': state and state.id or False, 'country_id': country and country.id or False,
                'is_company': False, 'lang': woo_instance.woo_lang_id.code,
            }
            woo_partner = partner_obj.woo_search_address_partner(partner_vals, address_key_list, parent_id,
                                                                 partner_type)
            if not woo_partner:
                woo_partner = partner_obj.create(partner_vals)
        return woo_partner
