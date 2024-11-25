# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import split_every

_logger = logging.getLogger("WooCommerce")


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_woo_customer = fields.Boolean(string="Is Woo Customer?",
                                     help="Used for identified that the customer is imported from WooCommerce store.")

    def woo_check_proper_response(self, response, instance):
        """
        This method checks for errors in received response from WooCommerce and creates log line for the issue.
        @param instance:
        @param response: Response from the WooCommerce.
        @author: Maulik Barad on Date 31-Oct-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        common_log_line_obj = self.env["common.log.lines.ept"]

        if not isinstance(response, requests.models.Response):
            message = "Import all customers \nResponse is not in proper format :: %s" % response
            common_log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                           woo_instance_id=instance.id, model_name=self._name,
                                                           message=message)

            return []
        if response.status_code not in [200, 201]:
            message = "Error in Import All Customers %s" % response.content
            common_log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                           woo_instance_id=instance.id, model_name=self._name,
                                                           message=message)
            return []
        try:
            data = response.json()
        except Exception as error:
            message = "Json Error : In import customers from WooCommerce. \n%s" % error
            common_log_line_obj.create_common_log_line_ept(operation_type="import", module="woocommerce_ept",
                                                           woo_instance_id=instance.id, model_name=self._name,
                                                           message=message)
            return []
        return data

    def woo_import_all_customers(self, wc_api, page, instance):
        """
        This method used to request for the customer page.
        @param : self, wc_api, common_log_id, page
        @author: Maulik Barad on Date 30-Oct-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        queue_ids = []

        try:
            res = wc_api.get('customers', params={"per_page": 100, 'page': page})
        except Exception as error:
            raise UserError(_("Something went wrong while importing Customers.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))

        response = self.woo_check_proper_response(res, instance)
        if response:
            queue_ids = self.create_woo_customer_queue(response, instance).ids
        return queue_ids

    @api.model
    def woo_get_customers(self, instance):
        """
        This method used to call the request of the customer and prepare a customer response.
        @param : self, common_log_id, instance
        @return: customers
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 28 August 2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        customer_queues = []

        wc_api = instance.woo_connect()
        try:
            response = wc_api.get('customers', params={"per_page": 100})
        except Exception as error:
            raise UserError(_("Something went wrong while importing Customers.\n\nPlease Check your Connection and "
                              "Instance Configuration.\n\n" + str(error)))
        customers = self.woo_check_proper_response(response, instance)
        if not customers:
            return customers
        total_pages = response.headers.get('X-WP-TotalPages')
        queues = self.create_woo_customer_queue(customers, instance)
        customer_queues += queues.ids
        if int(total_pages) >= 2:
            for page in range(2, int(total_pages) + 1):
                queue_ids = self.woo_import_all_customers(wc_api, page, instance)
                customer_queues += queue_ids
        return customer_queues

    def create_woo_customer_queue(self, customer_data, instance):
        """
        This method creates queues for customer and notifies user about that.
        @param instance:
        @param customer_data: Data of customer.
        @return: Records of Customer queues.
        @author: Maulik Barad on Date 30-Oct-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        bus_bus_obj = self.env['bus.bus']

        queues = self.woo_create_customer_queue(customer_data, instance)
        message = "Customer Queue created %s" % ', '.join(queues.mapped('name'))
        # bus_bus_obj._sendone(self.env.user.partner_id, 'simple_notification',
        #                      {'title': 'WooCommerce Connector', 'message': message, "sticky": False,
        #                       "warning": True})
        bus_bus_obj._sendone(self.env.user.partner_id, 'simple_notification',
                             {'title': _('WooCommerce Connector'), 'message': _(message), "sticky": False,
                              "warning": True})
        self._cr.commit()
        return queues

    def woo_create_customer_queue(self, customers, instance, created_by="import"):
        """
        This method used to create a customer queue base on the customer response.
        :param customers: Customer response as received from Woocommerce store.
        @return: queues: Record of customer queues
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 28 August 2020.
        Task_id: 165956
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_sync_customer_obj = queues = self.env['woo.customer.data.queue.ept']
        woo_sync_customer_data = self.env['woo.customer.data.queue.line.ept']

        for customer_queue in split_every(101, customers):
            queue = woo_sync_customer_obj.create({"woo_instance_id": instance.id, "created_by": created_by})
            _logger.info("Created customer queue: %s", queue.display_name)
            sync_vals = {'woo_instance_id': instance.id, 'queue_id': queue.id}

            for customer in customer_queue:
                existing_customer_data_queue_line = woo_sync_customer_data.search(
                    [('woo_synced_data_id', '=', customer.get('id')), ('woo_instance_id', '=', instance.id),
                     ('state', 'in', ['draft', 'failed'])])
                sync_vals.update({
                        'last_process_date': datetime.now(),
                        'woo_synced_data': json.dumps(customer),
                        'woo_synced_data_id': customer.get('id'),
                        'name': customer.get('first_name') + " " + customer.get('last_name') if customer.get(
                            'first_name') else customer.get('username')
                    })
                if not existing_customer_data_queue_line:
                    woo_sync_customer_data.create(sync_vals)
                else:
                    existing_customer_data_queue_line.update(sync_vals)
            queues += queue
        return queues

    def woo_create_contact_customer(self, vals, instance=False):
        """
        This method used to create a contact type customer.
        @param : self, vals, instance=False
        @return: partner
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 2 September 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_partner_obj = self.env['woo.res.partner.ept']

        partner = woo_partner = woo_customer_id = False
        woo_id = vals.get('id') or False
        contact_first_name = vals.get('first_name', '')
        contact_last_name = vals.get('last_name', '')
        contact_email = vals.get('email', '')

        contact_name = "%s %s" % (contact_first_name, contact_last_name)
        if not contact_first_name and not contact_last_name:
            return False
        if woo_id:
            woo_customer_id = "%s" % woo_id
            woo_partner = woo_partner_obj.search([("woo_customer_id", "=", woo_customer_id),
                                                  ("woo_instance_id", "=", instance.id)], limit=1)
        if woo_partner:
            partner = woo_partner.partner_id
            return partner
        woo_partner_values = {'woo_customer_id': woo_customer_id, 'woo_instance_id': instance.id}
        if contact_email:
            partner = self.search_partner_by_email(contact_email)

        # If partner is not found, then need to create it.
        if not partner:
            contact_partner_vals = ({'customer_rank': 1, 'is_woo_customer': True, 'type': 'contact',
                                     'name': contact_name, 'email': contact_email or False})
            if vals.get('billing') and vals.get('billing', {}).get('first_name') and vals.get('billing', {}).get(
                    'last_name'):
                contact_partner_vals = self.woo_prepare_partner_vals(vals.get('billing'), instance)
                contact_partner_vals.update({'customer_rank': 1, 'is_woo_customer': True, 'type': 'invoice'})

                company_name = vals.get("billing", {}).get("company")
                if company_name:
                    if instance.import_partner_as_company:
                        company_partner = self.woo_search_or_create_company_partner(company_name, create_company=True)
                        contact_partner_vals.update({"parent_id": company_partner.id})
                    else:
                        contact_partner_vals.update({"company_name": vals.get("billing", {}).get("company")})

            partner = self.create(contact_partner_vals)
        # If partner is found, then need to check if is_woo_customer is set or not in it.
        if not partner.is_woo_customer:
            partner.write({'is_woo_customer': True})

        partner.create_woo_res_partner_ept(woo_partner_values)
        return partner

    def create_woo_res_partner_ept(self, woo_partner_values):
        """
        This method use to create a Woocommerce layer customer.
        @param : self,woo_partner_values
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 31 August 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        woo_partner_obj = self.env['woo.res.partner.ept']
        woo_partner_values.update({'partner_id': self.id})
        return woo_partner_obj.create(woo_partner_values)

    def woo_search_address_partner(self, partner_vals, address_key_list, parent_id, partner_type):
        """
        This method searches for existing shipping/billing address.
        @param partner_vals: Dictionary of address data.
        @param address_key_list: Keys of address to check.
        @param parent_id: Id of existing partner, for searching in child of that partner.
        @param partner_type: Type of address to search for.
        @author: Maulik Barad on Date 31-Oct-2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        domain = [('type', '=', partner_type)]
        if parent_id:
            parent_domain = [('parent_id', '=', parent_id.id)]
            domain += parent_domain
        else:
            parent_domain = []
        address_partner = self._find_partner_ept(partner_vals, address_key_list, domain)
        if not address_partner:
            address_partner = self._find_partner_ept(partner_vals, address_key_list, parent_domain)
        if not address_partner:
            address_partner = self._find_partner_ept(partner_vals, address_key_list)
        return address_partner

    def woo_create_or_update_customer(self, customer_val, instance, parent_id, partner_type, customer_id=False):
        """
        This method used to create a billing and shipping address base on the customer val response.
        @param : self,customer_val,instance,parent_id,type
        @return: address_partner
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 2 September 2020 .
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        _logger.info("Creating %s type of Partner... " % partner_type)
        company_partner = False
        address_key_list = ['name', 'street', 'street2', 'city', 'zip', 'phone', 'state_id', 'country_id']

        first_name = customer_val.get("first_name")
        last_name = customer_val.get("last_name")
        contact_email = customer_val.get('email', '')
        if not first_name and not last_name:
            return False
        if contact_email:
            parent_id = self.search_partner_by_email(contact_email)
        company_name = customer_val.get("company")
        partner_vals = self.woo_prepare_partner_vals(customer_val, instance)
        woo_partner_values = {'woo_customer_id': customer_id, 'woo_instance_id': instance.id}

        if partner_type == 'delivery':
            address_key_list.remove("phone")
        if company_name:
            if instance.import_partner_as_company:
                company_partner = self.woo_search_or_create_company_partner(company_name, parent_id)
                parent_id = company_partner if company_partner else parent_id
            else:
                address_key_list.append('company_name')
                partner_vals.update({'company_name': company_name})

        address_partner = self.woo_search_address_partner(partner_vals, address_key_list, parent_id, partner_type)

        if company_name and instance.import_partner_as_company:
            _logger.info("Creating company from %s..." % company_name)
            company_partner = self.woo_search_or_create_company_partner(
                company_name, False if address_partner == parent_id else parent_id, create_company=True)
            parent_id = company_partner

        if address_partner:
            _logger.info("Existing partner found %s - %s." % (address_partner, address_partner.name))
            if customer_id and not address_partner.is_woo_customer:
                address_partner.create_woo_res_partner_ept(woo_partner_values)
                address_partner.write({'is_woo_customer': True})
            if not address_partner.parent_id and address_partner != parent_id and company_partner:
                address_partner.parent_id = company_partner
            return address_partner

        if 'company_name' in partner_vals:
            partner_vals.pop('company_name')
        if parent_id:
            partner_vals.update({'parent_id': parent_id.id})
        partner_vals.update({'type': partner_type})
        address_partner = self.create(partner_vals)

        if customer_id:
            address_partner.create_woo_res_partner_ept(woo_partner_values)
            address_partner.write({'is_woo_customer': True})

        if company_name and not instance.import_partner_as_company:
            address_partner.write({'company_name': company_name})

        _logger.info("Created new partner: %s." % address_partner)

        return address_partner

    def woo_prepare_partner_vals(self, vals, instance):
        """
        This method used to prepare a partner vals.
        @param : self,vals,instance
        @return: partner_vals
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 29 August 2020.
        Migrated by Maulik Barad on Date 07-Oct-2021.
        """
        email = vals.get("email", False)
        first_name = vals.get("first_name")
        last_name = vals.get("last_name")
        name = "%s %s" % (first_name, last_name)
        phone = vals.get("phone")
        address1 = vals.get("address_1")
        address2 = vals.get("address_2")
        city = vals.get("city")
        zipcode = vals.get("postcode")
        state_code = vals.get("state")
        country_code = vals.get("country")

        country = self.get_country(country_code)
        state = self.create_or_update_state_ept(country_code, state_code, False, country)

        partner_vals = {
            'email': email or False, 'name': name, 'phone': phone,
            'street': address1, 'street2': address2, 'city': city, 'zip': zipcode,
            'state_id': state and state.id or False, 'country_id': country and country.id or False,
            'is_company': False, 'lang': instance.woo_lang_id.code,
        }
        update_partner_vals = self.remove_special_chars_from_partner_vals(partner_vals)
        return update_partner_vals

    def woo_search_or_create_company_partner(self, company_name, parent_partner=False, create_company=False):
        """
        Searches for the company type partner and creates new partner if not found.
        @author: Maulik Barad on Date 15-Sep-2022.
        """
        company = self.search([("name", "=", company_name), ("is_company", "=", True)])
        if not company and create_company:
            parent_partner = parent_partner.parent_id if parent_partner and parent_partner.parent_id else parent_partner
            company = self.create({"name": company_name, "is_company": True,
                                   "customer_rank": 1,
                                   "parent_id": parent_partner and parent_partner.id or False})
        return company
