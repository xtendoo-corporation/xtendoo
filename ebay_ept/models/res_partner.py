# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import importlib
import sys
from odoo import models, fields

importlib.reload(sys)


class ResPartner(models.Model):
    _inherit = "res.partner"

    ebay_eias_token = fields.Char('EIAS Token', size=256)
    ebay_reg_date = fields.Char('Registration Date', size=64)
    ebay_user_id = fields.Char('User ID', size=64)
    ebay_user_id_last_changed = fields.Char('User ID Last Changed', size=64)
    ebay_user_email_id = fields.Char('User Email', size=100)
    ebay_address_id = fields.Char('Address ID', size=64)

    def create_or_update_ebay_partner(self, order_response, instance):
        """
        Creates or update customer for particular eBay site.
        When MultiLegShippingDetails that time it will take 'ReferenceId' as 'ebay_address_id' at partner create time
        and if partner already exist then it will write referenceId in ebay address id.
        Task : 171947 , @last_update_on : 10/03/2021
        """
        partner_values, buyer_name = self.prepare_customer_ebay_values(order_response, instance)
        ebay_user_id = partner_values.get('ebay_user_id')
        partner_values.update({'name': buyer_name, 'type': 'invoice'})
        exist_partner = self.search([('ebay_user_id', '=', ebay_user_id)], limit=1)
        is_multi_address = False
        if order_response.get('IsMultiLegShipping').lower() == 'true' and order_response.get('MultiLegShippingDetails'):
            is_multi_address = True
        if exist_partner:
            if is_multi_address:
                exist_partner.ebay_address_id = partner_values.get('ebay_address_id', False)
            exist_child_partner = self.find_ebay_partner_by_key(partner_values)
            if not exist_child_partner:
                shipping_partner = self.create_ebay_delivery_partner(partner_values, exist_partner)
            else:
                shipping_partner = exist_child_partner
                if is_multi_address:
                    shipping_partner.ebay_address_id = partner_values.get('ebay_address_id', False)
        else:
            exist_partner = self.with_context(tracking_disable=True).create(
                {'name': buyer_name, 'ebay_user_id': partner_values.get('ebay_user_id'),
                'email': partner_values.get('email')})
            shipping_partner = self.create_ebay_delivery_partner(partner_values, exist_partner)

        return exist_partner, shipping_partner

    def prepare_customer_ebay_values(self, order_response, instance):
        """
        This method prepare the customer values
        :param order_response: Order Response from eBay GetOrder API
        :param instance: Instance of eBay
        :return: customer values dictionary
        Added MultiLegShippingDetails related condition. when MultiLegShippingDetails then take ShipToAddress other
        case take ShippingAddress and also when MultiLegShippingDetails then it will take "ReferenceId" as 'ebay
        address id' otherwise it takes as it is 'AddressID'
        Date : 10/03/2021 , Task : 171947
        Migration done by Haresh Mori @ Emipro on date 7 January 2022 .
        """
        state = False
        address_info = order_response.get('ShippingAddress', {}) if not order_response.get(
            'IsMultiLegShipping').lower() == 'true' and not order_response.get('MultiLegShippingDetails',
                                                                               {}) else order_response.get(
            'MultiLegShippingDetails', {}).get('SellerShipmentToLogisticsProvider', {}).get('ShipToAddress', {})
        transaction_array = order_response['TransactionArray'].get('Transaction', False)
        order_transaction = order_response['TransactionArray']['Transaction']
        transaction = order_response.get('TransactionArray', False) and transaction_array and order_transaction or {}
        if isinstance(transaction, list):
            transaction = transaction[0]

        email, ship_name, buyer_name = self.ebay_prepare_emai_shiper_buyer_name(transaction, address_info)

        country_code = address_info.get('Country')
        country = self.get_country(country_code)
        state_or_province = address_info.get('StateOrProvince', False)
        zipcode = address_info.get('PostalCode', False)
        if state_or_province:
            state = self.create_or_update_state_ept(country_code, state_or_province, zipcode, country)

        partner_values = self.prepare_ebay_customer_vals(ship_name, address_info, state, country, email, instance,
                                                         order_response)
        return partner_values, buyer_name

    def ebay_prepare_emai_shiper_buyer_name(self, transaction, address_info):
        """
        This method is use to prepare email, shipper and buyer name.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 7 January 2022 .
        Task_id: 180140 - Import Unshipped Orders
        """
        email = user_first_name = user_last_name = buyer_name = ''
        if transaction.get('Buyer', False):
            email = transaction['Buyer'].get('Email', False)
            user_first_name = transaction['Buyer'].get('UserFirstName', False)
            user_last_name = transaction['Buyer'].get('UserLastName', False)
        ship_name = address_info.get('Name', 'eBay Customer')
        if ship_name == 'None' or ship_name is None:
            ship_name = 'eBay Customer'
        if user_first_name is not None and user_last_name is not None:
            buyer_name = user_first_name + ' ' + user_last_name
        buyer_name = buyer_name if buyer_name else ship_name
        return email, ship_name, buyer_name

    def prepare_ebay_customer_vals(self, ship_name, address_info, state, country, email, instance, order):
        """
        This method is use to prepare customer vals.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 7 January 2022 .
        Task_id: 180140 - Import Unshipped Orders
        """
        partner_values = {
            'name': ship_name,
            'street': address_info.get('Street1', False),
            'street2': address_info.get('Street2', False),
            'zip': address_info.get('PostalCode', False),
            'city': address_info.get('CityName', False),
            'state_id': state and state.id or False,
            'country_id': country and country.id or False,
            'phone': address_info.get('Phone', False),
            'email': email,
            'lang': instance.lang_id.code,
            'ebay_user_email_id': email,
            'ebay_address_id': address_info.get('AddressID', False) if not order.get(
                'IsMultiLegShipping').lower() == 'true' and not order.get('MultiLegShippingDetails',
                                                                          {}) else address_info.get('ReferenceID',
                                                                                                    False),
            'ebay_user_id': order.get('BuyerUserID', False),
            'ebay_eias_token': order.get('EIASToken', False)
        }
        if instance.ebay_property_account_receivable_id:
            partner_values.update({'property_account_receivable_id': instance.ebay_property_account_receivable_id.id})
        if instance.ebay_property_account_payable_id:
            partner_values.update({'property_account_payable_id': instance.ebay_property_account_payable_id.id})
        return partner_values

    def create_ebay_delivery_partner(self, partner_values, parent_id):
        """
        Creates new invoice type partner.
        :param partner_values: Dictionary of partner values.
        :param parent_id: Parent partner object
        :return: res partner object
        """
        partner_values.update({'type': 'delivery', 'parent_id': parent_id.id})
        shipping_partner = self.with_context(tracking_disable=True).create(partner_values)
        return shipping_partner

    def find_ebay_partner_by_key(self, partner_values):
        """
        Find Partner by specific parameters
        :param partner_values: Partner values dictionary.
        :return: res partner object or False
        Migration done by Haresh Mori @ Emipro on date 7 January 2022 .
        """
        key_list = ['name']
        if partner_values.get('street'):
            key_list.append('street')
        if partner_values.get('street2'):
            key_list.append('street2')
        if partner_values.get('city'):
            key_list.append('city')
        if partner_values.get('zip'):
            key_list.append('zip')
        if partner_values.get('phone'):
            key_list.append('phone')
        if partner_values.get('state_id'):
            key_list.append('state_id')
        if partner_values.get('country_id'):
            key_list.append('country_id')
        exist_partner = self._find_partner_ept(partner_values, key_list)
        return exist_partner
