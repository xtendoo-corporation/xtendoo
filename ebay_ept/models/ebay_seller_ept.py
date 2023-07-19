#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods and fields for eBay Seller
"""
import string
import random
from calendar import monthrange
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..ebaysdk.trading import Connection as trading
import requests
import base64

_IR_CRON = 'ir.cron'

_secondsConverter = {
    'days': lambda interval: interval * 24 * 60 * 60,
    'hours': lambda interval: interval * 60 * 60,
    'weeks': lambda interval: interval * 7 * 24 * 60 * 60,
    'minutes': lambda interval: interval * 60,
}


class EbaySellerEpt(models.Model):
    """
    Describes eBay sellers
    """
    _name = 'ebay.seller.ept'
    _description = 'Ebay Sellers'

    @api.model
    def _get_default_shipment_ebay_fee(self):
        return self.env.ref('ebay_ept.product_product_ebay_shipment_fee', False)

    @api.model
    def _get_default_order_discount(self):
        return self.env.ref('ebay_ept.product_product_ebay_order_discount')

    name = fields.Char(size=120, string='Seller Name', required=True)
    instance_ids = fields.One2many("ebay.instance.ept", "seller_id", "eBay Instances", help="eBay Instance ids.")
    dev_id = fields.Char('Dev ID', size=256, required=True, help="eBay Dev ID")
    app_id = fields.Char('App ID', size=256, required=True, help="eBay App ID")
    cert_id = fields.Char('Cert ID', size=256, required=True, help="eBay Cert ID")
    server_url = fields.Char('Server URL', size=256, help="eBay Server URL")
    environment = fields.Selection([
        ('is_sandbox', 'Sandbox'), ('is_production', 'Production')], 'eBay Environment', required=True)
    auth_token = fields.Text('Token', help="eBay Token")
    company_id = fields.Many2one('res.company', string="Company")
    country_id = fields.Many2one("res.country", "Country")
    ebay_plus = fields.Boolean("Is eBay Plus Account", default=False)
    shipment_charge_product_id = fields.Many2one(
        "product.product", "Shipment Fee", domain=[('type', '=', 'service')], default=_get_default_shipment_ebay_fee)
    discount_charge_product_id = fields.Many2one(
        "product.product", "Order Discount", domain=[('type', '=', 'service')], default=_get_default_order_discount)
    use_dynamic_desc = fields.Boolean(
        "Use Dynamic Description",
        help='If ticked then you can able to use dynamic product description for an individual product only.')
    email_add = fields.Char('Email Address', size=126, help="Seller Email Address")
    is_auto_get_feedback = fields.Boolean(string="Auto Get FeedBacks?")
    order_auto_import = fields.Boolean(string='Auto Order Import?')
    ebay_order_auto_update = fields.Boolean(string="Auto Order Update ?")
    stock_auto_export = fields.Boolean(string="Auto Stock Export?")
    auto_update_payment = fields.Boolean(string="Auto Update Payment In eBay On invoice paid ?")
    auto_sync_active_products = fields.Boolean(
        string="Auto Sync. Active Products ?", help="Auto Sync. Active Products ?")
    sync_active_products_start_date = fields.Date(
        string="Sync. Active Products Start Date", help="Sync. Active Products Start Date")
    auto_send_invoice_via_email = fields.Boolean(
        string="Auto Send Invoice Via Email ?", help="Auto Send Invoice Via Email.")
    send_invoice_template_id = fields.Many2one("mail.template", "Invoice Template")
    is_import_shipped_order = fields.Boolean(
        string="Import Shipped Orders?", default=False, help="Import Shipped Orders.")
    last_ebay_order_import_date = fields.Datetime('Last Order Import  Time', help="Order was last Imported On")
    last_update_order_export_date = fields.Datetime(
        'Last Order Update  Time', help="Order Status was last Updated On")
    order_prefix = fields.Char(size=10, string='eBay Order Prefix', help="eBay Order Prefix name")
    ebay_team_id = fields.Many2one('crm.team', 'Sales Team', help="Set eBay Seller Sales Team")
    create_new_product = fields.Boolean("Create New Odoo Product", default=False)
    order_import_days = fields.Char(size=10, string='eBay Order Import Days', help="eBay Order Import Days")
    payment_option_ids = fields.One2many("ebay.payment.options", "seller_id", help="Payment Options for eBay site")
    cron_count = fields.Integer(
        "Scheduler Count", compute="_compute_get_scheduler_list", help="This Field relocates Active Scheduler Count.")
    state = fields.Selection([
        ('not_confirmed', 'Not Confirmed'), ('confirmed', 'Confirmed')], default='not_confirmed')
    ebay_is_use_default_sequence = fields.Boolean(
        "Use Odoo Default Sequence in eBay Orders?",
        help="If checked,Then use default sequence of odoo while create sale order imported from eBay.")
    ebay_is_create_delivery_carrier = fields.Boolean(
        string="Is eBay Delivery Carrier Create?",
        help="If checked, then create delivery carrier in case not found when import sale order from eBay")
    ebay_is_sync_stock = fields.Boolean(
        "Is product stock synced?", default=False, help="Is product stock synced when Sync/import products?")
    ebay_is_sync_price = fields.Boolean(
        "Is product price synced?", default=False, help="Is product price synced when Sync/import products?")

    # Stores authorization(app_id:cert_id), which is needed for OAuth 2.0 access token.
    authorization = fields.Char(compute="_compute_get_authorization", store=True)
    oauth_access_token = fields.Char()  # stores OAuth 2.0 access_token

    @api.depends('app_id', 'cert_id')
    def _compute_get_authorization(self):
        """
        Compute authorization for each record.
        @author: Neha Joshi @Emipro Technologies Pvt. Ltd. date: 29/09/2022
        Task id : 202082
        """
        for rec in self:
            str_to_convert = rec.app_id + ":" + rec.cert_id
            b = base64.b64encode(bytes(str_to_convert, 'utf-8'))
            base64_str = b.decode('utf-8')
            authorization = 'Basic %s' % base64_str
            rec.authorization = authorization

    def generate_access_token_for_taxonomy_api(self):
        """
        OAuth 2.0 access token is created and stored in self.oauth_access_toke
        @author: Neha Joshi @Emipro Technologies Pvt. Ltd. date: 29/09/2022
        Task id : 202082
        """
        oauth_access_token = True
        header = {'Content-Type': 'application/x-www-form-urlencoded',
                  'Authorization': self.authorization}
        data = {"grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope"}

        url_domain = 'api.ebay.com' if self.environment == 'is_production' else 'api.sandbox.ebay.com'

        ebay_auth_url = "https://%s/identity/v1/oauth2/token" % url_domain
        auth_response = requests.post(ebay_auth_url, data=data, headers=header)
        auth_response_json = auth_response.json()
        if auth_response_json.get('access_token'):
            oauth_access_token = auth_response_json.get('access_token')
            self.oauth_access_token = oauth_access_token
        return oauth_access_token

    def _compute_get_scheduler_list(self):
        """
        Compute and get cron of eBay Seller
        :return:
        """
        seller_cron = self.env[_IR_CRON].search([('ebay_seller_cron_id', '=', self.id)])
        for record in self:
            record.cron_count = len(seller_cron.ids)

    def list_of_seller_cron(self):
        """
        Redirect to the seller cron wizard
        :return: Run the seller cron wizard action.
        """
        seller_cron = self.env[_IR_CRON].search([('ebay_seller_cron_id', '=', self.id)])
        action = {
            'domain': "[('id', 'in', " + str(seller_cron.ids) + " )]",
            'name': 'Cron Scheduler',
            'view_mode': 'tree,form',
            'res_model': _IR_CRON,
            'type': 'ir.actions.act_window',
        }
        return action

    @api.model_create_multi
    def create(self, vals_list):
        """
        Creates eBay seller details
        :param vals_list: values to create eBay details
        :return: ebay seller object
        """
        payment_option_obj = self.env['ebay.payment.options']
        for vals in vals_list:
            sales_team = self.create_sales_team(vals.get('name'))
            vals.update({"ebay_team_id": sales_team.id})
        seller_ids = super(EbaySellerEpt, self).create(vals_list)
        for seller in seller_ids:
            try:
                trading_api = seller.get_trading_api_object()
                para = {}
                # pass parameters in GeteBayDetails sandbox API is temporary.
                # Because in sandbox shipping services are not fetched.
                # once API works perfect, pass parameter code will be removed.
                if seller.environment == 'is_sandbox':
                    para = {
                        "DetailName": [
                            "SiteDetails", "PaymentOptionDetails", "ReturnPolicyDetails",
                            "BuyerRequirementDetails", "ShippingLocationDetails"]}
                trading_api.execute('GeteBayDetails', para)
                results = trading_api.response.dict()
                if results:
                    payment_option_obj.get_payment_options(seller, results.get('PaymentOptionDetails', []))
            except Exception as error:
                seller.unlink()
                raise UserError(error)
        return seller_ids

    @api.onchange('environment')
    def onchange_environment(self):
        """
        Set Server URL based on eBay environment.
        """
        if self.environment == 'is_sandbox':
            server_url = 'https://api.sandbox.ebay.com/ws/api.dll'
        else:
            server_url = 'https://api.ebay.com/ws/api.dll'
        self.server_url = server_url

    @api.model
    def get_ebay_official_time(self):
        """
        Get eBay Official Time
        :return: Official time or raise warning
        """
        try:
            trading_api = self.get_trading_api_object()
            trading_api.execute('GeteBayOfficialTime', {})
            results = trading_api.response.dict()
            return results.get('Timestamp', False) and results['Timestamp'][:19] + '.000Z'
        except Exception:
            raise UserError(_("Call GeteBayOfficialTime API time error."))

    def get_ebay_cron_execution_time(self, cron_name):
        """
        This method is used to get the interval time of the cron.
        @param cron_name: External ID of the Cron.
        @return: Interval time in seconds.
        """
        process_queue_cron = self.env.ref(cron_name, False)
        if not process_queue_cron:
            raise UserError(_("Please upgrade the module. \n Maybe the job has been deleted, it will be recreated at "
                              "the time of module upgrade."))
        interval = process_queue_cron.interval_number
        interval_type = process_queue_cron.interval_type
        if interval_type == "months":
            days = 0
            current_year = fields.Date.today().year
            current_month = fields.Date.today().month
            for i in range(0, interval):
                month = current_month + i

                if month > 12:
                    if month == 13:
                        current_year += 1
                    month -= 12

                days_in_month = monthrange(current_year, month)[1]
                days += days_in_month

            interval_type = "days"
            interval = days
        interval_in_seconds = _secondsConverter[interval_type](interval)
        return interval_in_seconds

    def create_sales_team(self, name):
        """
        Creates new sales team for eBay instance.
        :param name: Sales team name
        """
        crm_team_obj = self.env['crm.team']
        sales_team_values = {'name': name, 'use_quotations': True}
        return crm_team_obj.create(sales_team_values)

    def create_site_details(self):
        """
        Checks available eBay Sites if not then create them.
        """
        trading_api = self.get_trading_api_object()
        para = {}
        # pass parameters in GeteBayDetails sandbox API is temporary.
        # Because in sandbox shipping services are not fetched.
        # once API works perfect, pass parameter code will be removed.
        if self.environment == 'is_sandbox':
            para = {
                "DetailName": [
                    "SiteDetails", "PaymentOptionDetails", "ReturnPolicyDetails",
                    "BuyerRequirementDetails", "ShippingLocationDetails"]}
        trading_api.execute('GeteBayDetails', para)
        results = trading_api.response.dict()
        self.env['ebay.site.details'].get_site_details(results.get('SiteDetails', False))
        return True

    @api.model
    def get_trading_api_object(self):
        """
        Get Trading API object of eBay.
        :return: api response
        """
        if self.environment == 'is_sandbox':
            domain = 'api.sandbox.ebay.com'
        else:
            domain = 'api.ebay.com'
        trading_api = trading(
            config_file=False, appid=self.app_id, devid=self.dev_id, certid=self.cert_id,
            token=self.auth_token, domain=domain, timeout=500)
        return trading_api

    def search_ebay_seller(self):
        """ This method used to search the shopify instance.
            :return: Record of shopify instance
            @author: Dipak Gogiya, 26/09/2020
            @Task:   166992
        """
        company = self.env.company or self.env.user.company_id
        seller = self.search(
            [('is_ebay_seller_create_from_on_boarding_panel', '=', True),
             ('is_ebay_on_boarding_configurations_done', '=', False),
             ('company_id', '=', company.id)], limit=1, order='id desc')
        if not seller:
            seller = self.search([('company_id', '=', company.id),
                                  ('is_ebay_on_boarding_configurations_done', '=', False)], limit=1, order='id desc')
            seller.write({'is_ebay_seller_create_from_on_boarding_panel': True})
        return seller

    def check_connection(self):
        """
        Check eBay connection with Odoo
        """
        trading_api = self.get_trading_api_object()
        para = {}
        try:
            trading_api.execute('GetUser', para)
        except Exception as error:
            raise UserError(error)
        raise UserError(_('Service working properly'))

    def ebay_credential_update(self):
        """
        Open view to update ebay credentials
        """
        ebay_credential_view = self.env.ref('ebay_ept.ebay_credential_upadte_wizard', False)
        result = True
        if ebay_credential_view:
            result = {
                'name': 'eBay Credential',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'ebay.credential',
                'type': 'ir.actions.act_window',
                'view_id': ebay_credential_view.id,
                'target': 'new'
            }
        return result

    def confirm(self):
        """
        Confirm instance status
        """
        if self.state != 'confirmed':
            trading_api = self.get_trading_api_object()
            para = {}
            try:
                trading_api.execute('GetUser', para)
            except Exception as error:
                raise UserError(error)
            self.write({'state': 'confirmed'})
        return True

    def reset_to_confirm(self):
        """
        Reset instance not to confirmed status.
        """
        self.write({'state': 'not_confirmed'})
        return True

    def ebay_cron_configuration_action(self):
        """
        Open view for eBay cron configuration
        """
        action = self.env.ref('ebay_ept.action_wizard_ebay_cron_configuration_ept').read()[0]
        action['context'] = {'ebay_seller_id': self.id}
        return action

    @api.model
    def auto_get_feedback(self, args=None):
        """
        This method is use to get the feedback from eBay store to odoo via cron job.
        Migration done by Haresh Mori @ Emipro on date 13 January 2022 .
        """
        if args is None:
            args = {}
        ebay_feedback_obj = self.env['ebay.feedback.ept']
        seller_id = args.get('seller_id')
        if seller_id:
            instances = self.browse(seller_id).instance_ids
            ebay_feedback_obj.with_context(is_auto_process=True).get_feedback(instances)
        return True

    @api.model
    def auto_import_ebay_sales_orders(self, args=None):
        """
        This method is use to import the unshipped order from eBay to Odoo via cron job.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 12 January 2022 .
        """
        order_queue_obj = self.env["ebay.order.data.queue.ept"]
        if args is None:
            args = {}
        seller_id = args.get('seller_id')
        if seller_id:
            seller = self.browse(seller_id)
            order_queue_obj.import_unshipped_orders_from_ebay(seller)
        return True

    @api.model
    def auto_update_order_status(self, args=None):
        """
        Update eBay Order Status automatically
        :param args: dictionary of arguments
        """
        if args is None:
            args = {}
        sale_order_obj = self.env['sale.order']
        seller_id = args.get('seller_id')
        if seller_id:
            instances = self.browse(seller_id).instance_ids
            for instance in instances:
                sale_order_obj.ebay_update_order_status(instance)
        return True

    @api.model
    def auto_export_inventory_ept(self, args=None):
        """
        Update stock from Odoo to eBay automatically
        :param args: dictionary of arguments
        """
        if args is None:
            args = {}
        ebay_product_obj = self.env['ebay.product.product.ept']
        seller_id = args.get('seller_id')
        if seller_id:
            instances = self.browse(seller_id).instance_ids
            for instance in instances:
                ebay_product_obj.export_stock_in_ebay(instance)
        return True

    @api.model
    def auto_sync_active_products_listings(self, args=None):
        """
        This method is use to import automatically products from eBay to Odoo.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 11 December 2021 .
        Task_id: 180925 - Import Products / variants
        """
        process_import_export_obj = self.env["ebay.process.import.export"]
        if args is None:
            args = {}
        seller_id = args.get('seller_id')
        if seller_id:
            seller = self.browse(seller_id)
            process_import_export_obj.with_context(is_call_from_cron=True).ebay_sync_import_products(seller)
        return True

    def get_email_template_for_invoice(self, instances):
        """
        Get email template from instance or default invoice email template.
        :param instances: eBay instances object
        :return: email template
        """
        if instances[0].seller_id.send_invoice_template_id:
            email_template = instances.seller_id.send_invoice_template_id
        else:
            email_template = self.env.ref('account.email_template_edi_invoice', False)
        return email_template
