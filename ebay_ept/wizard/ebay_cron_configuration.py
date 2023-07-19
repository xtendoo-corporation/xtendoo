#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes eBay Seller Cron configurations
"""
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_INTERVALTYPES = {
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7 * interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}


class EbayCronConfiguration(models.TransientModel):
    """
    Describes eBay Seller Cron configurations
    """
    _name = "ebay.cron.configuration"
    _description = "eBay Cron Configuration"

    def _get_ebay_seller(self):
        return self.env.context.get('ebay_seller_id', False)

    ebay_seller_id = fields.Many2one('ebay.seller.ept', string='eBay sellers', default=_get_ebay_seller, readonly=True)
    ebay_order_auto_update = fields.Boolean(string="Auto Order Update ?", default=False)
    # Auto sync. active product
    ebay_auto_sync_active_products = fields.Boolean(
        string="eBay Auto Sync. Active Products ?", help="Auto Sync. Active Products ?")
    ebay_sync_active_products_interval_number = fields.Integer(
        string="eBay Auto Sync. Active Products Interval Number", help="Repeat every x.")
    ebay_sync_active_products_interval_type = fields.Selection([
        ('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')
    ], string="eBay Auto Sync. Active Products Interval Unit")
    ebay_sync_active_products_next_execution = fields.Datetime(
        string="eBay Next Execution of Sync. Active Product", help="Next Execution Time")
    ebay_sync_active_products_user_id = fields.Many2one(
        "res.users", string="eBay Sync. Active Products By User", help="User Name")
    ebay_sync_active_products_start_date = fields.Date(
        string="eBay Sync. Active Products Start Date", help="Sync. Active Products Start Date")
    ebay_auto_update_payment = fields.Boolean(string="eBay Auto Update Payment On Invoice Paid ?")
    ebay_order_auto_import = fields.Boolean(string='eBay Auto Order Import ?')
    ebay_order_import_interval_number = fields.Integer(
        string='eBay Import Order Interval Number', help="Repeat every x.")
    ebay_order_import_interval_type = fields.Selection([
        ('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')
    ], string='eBay Import Order Interval Unit')
    ebay_order_import_next_execution = fields.Datetime(
        string='eBay Next Execution of Import Order', help='Next execution time')
    is_ebay_auto_get_feedback = fields.Boolean(string="eBay Auto Get FeedBacks ?")
    get_ebay_feedback_interval_number = fields.Integer(
        string='eBay Import Feedback Interval Number', help="Repeat every x.")
    get_ebay_feedback_interval_type = fields.Selection([
        ('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')
    ], string='eBay Import Feedback Interval Unit')
    get_ebay_feedback_next_execution = fields.Datetime(
        string='eBay Next Execution of Import Feedback', help='Next execution time')
    get_ebay_feedback_user_id = fields.Many2one('res.users', string="eBay Feedback", help='User')
    ebay_stock_auto_export = fields.Boolean(string="eBay Auto Inventory Export ?")
    ebay_update_stock_interval_number = fields.Integer(
        string='eBay Update Stock Interval Number', help="Repeat every x.")
    ebay_update_stock_interval_type = fields.Selection([
        ('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')
    ], string='eBay Update Stock Interval Unit')
    ebay_update_stock_next_execution = fields.Datetime(
        string='eBay Next Execution of Update Stock', help='Next execution time')
    ebay_order_import_user_id = fields.Many2one(
        'res.users', string="eBay Import Order By User", help='User')
    ebay_order_update_interval_number = fields.Integer(
        string='eBay Update Order Interval Number', help="Repeat every x.")
    ebay_order_update_interval_type = fields.Selection([
        ('minutes', 'Minutes'), ('hours', 'Hours'), ('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months')
    ], string='eBay Update Order Interval Unit')
    ebay_order_update_next_execution = fields.Datetime(
        string='eBay Next Execution of Update Order', help='Next execution time')
    ebay_order_status_update_user_id = fields.Many2one(
        'res.users', string="eBay Update Order Status By User", help='User')
    ebay_stock_update_user_id = fields.Many2one('res.users', string="eBay Stock Update By User", help='User')

    @api.constrains("ebay_sync_active_products_interval_number", "ebay_update_stock_interval_number",
                    "ebay_order_import_interval_number", "get_ebay_feedback_interval_number")
    def check_interval_time(self):
        """
        It does not let set the cron execution time to Zero.
        @author: Haresh Mori on Date 11-Dec-2021.
        """
        for record in self:
            is_zero = False
            if record.ebay_auto_sync_active_products and record.ebay_sync_active_products_interval_number <= 0:
                is_zero = True
            if record.ebay_stock_auto_export and record.ebay_update_stock_interval_number <= 0:
                is_zero = True
            if record.ebay_order_auto_import and record.ebay_order_import_interval_number <= 0:
                is_zero = True
            if record.is_ebay_auto_get_feedback and record.get_ebay_feedback_interval_number <= 0:
                is_zero = True
            if record.ebay_order_auto_update and record.ebay_order_update_interval_number <= 0:
                is_zero = True
            if is_zero:
                raise UserError(_("Cron Execution Time can't be set to 0(Zero). "))

    @api.onchange("ebay_seller_id")
    def onchange_ebay_seller_id(self):
        """
        Set default cron configurations which was saved earlier for seller.
        """
        seller = self.ebay_seller_id
        self.get_feedback_cron_update(seller)
        self.order_import_cron_update(seller)
        self.order_status_update_cron_update(seller)
        self.update_stock_cron_update(seller)
        self.auto_sync_active_products_update(seller)

    def get_feedback_cron_update(self, seller):
        """
        Get values of get Feedback cron for a seller
        :param seller: seller of eBay
        """
        cron_exist = self.check_cron_exist_or_not('ir_cron_get_feedback_', seller)
        if cron_exist:
            self.is_ebay_auto_get_feedback = cron_exist.active or False
            self.get_ebay_feedback_interval_number = cron_exist.interval_number or False
            self.get_ebay_feedback_interval_type = cron_exist.interval_type or False
            self.get_ebay_feedback_next_execution = cron_exist.nextcall or False
            self.get_ebay_feedback_user_id = cron_exist.user_id.id or False

    def order_import_cron_update(self, seller):
        """
        Get values of order import cron for a seller
        :param seller: seller of eBay
        """
        cron_exist = self.check_cron_exist_or_not('ir_cron_send_ebay_import_sales_orders_seller_', seller)
        if cron_exist:
            self.ebay_order_auto_import = cron_exist.active or False
            self.ebay_order_import_interval_number = cron_exist.interval_number or False
            self.ebay_order_import_interval_type = cron_exist.interval_type or False
            self.ebay_order_import_next_execution = cron_exist.nextcall or False
            self.ebay_order_import_user_id = cron_exist.user_id.id or False

    def order_status_update_cron_update(self, seller):
        """
        Get values of order status update cron for a seller
        :param seller: seller of eBay
        """
        cron_exist = self.check_cron_exist_or_not('ir_cron_update_order_status_seller_', seller)
        if cron_exist:
            self.ebay_order_auto_update = cron_exist.active or False
            self.ebay_order_update_interval_number = cron_exist.interval_number or False
            self.ebay_order_update_interval_type = cron_exist.interval_type or False
            self.ebay_order_update_next_execution = cron_exist.nextcall or False
            self.ebay_order_status_update_user_id = cron_exist.user_id.id or False

    def update_stock_cron_update(self, seller):
        """
        Get values of update stock cron for a seller
        :param seller: seller of eBay
        """
        cron_exist = self.check_cron_exist_or_not('ir_cron_auto_export_inventory_seller_', seller)
        if cron_exist:
            self.ebay_stock_auto_export = cron_exist.active or False
            self.ebay_update_stock_interval_number = cron_exist.interval_number or False
            self.ebay_update_stock_interval_type = cron_exist.interval_type or False
            self.ebay_update_stock_next_execution = cron_exist.nextcall or False
            self.ebay_stock_update_user_id = cron_exist.user_id.id or False

    def auto_sync_active_products_update(self, seller):
        """
        Get values of Sync active products cron for a seller
        :param seller: seller of eBay
        """
        cron_exist = self.check_cron_exist_or_not('ir_cron_auto_sync_active_products_seller_', seller)
        if cron_exist:
            sync_active_products_start_date = seller.sync_active_products_start_date
            self.ebay_auto_sync_active_products = cron_exist.active or False
            self.ebay_sync_active_products_start_date = sync_active_products_start_date or False
            self.ebay_sync_active_products_interval_number = cron_exist.interval_number or False
            self.ebay_sync_active_products_interval_type = cron_exist.interval_type or False
            self.ebay_sync_active_products_next_execution = cron_exist.nextcall or False
            self.ebay_sync_active_products_user_id = cron_exist.user_id.id or False

    def check_cron_exist_or_not(self, cron_xml_name, seller):
        """
        Check cron is exist or not.
        :param cron_xml_name: Cron XML id reference
        :param seller: eBay seller object
        :return: True if cron is exist or False
        """
        try:
            cron_exist = seller and self.env.ref('ebay_ept.%s%d' % (cron_xml_name, seller.id))
        except Exception:
            cron_exist = False
        return cron_exist

    def save_cron_configuration(self):
        """
        Save selected cron configuration for a seller.
        """
        seller = self.ebay_seller_id
        self.ebay_setup_get_feedback_cron(seller)
        self.ebay_setup_order_import_cron(seller)
        self.ebay_setup_order_status_update_cron(seller)
        self.ebay_setup_update_stock_cron(seller)
        self.ebay_setup_auto_sync_active_products(seller)
        values = {
            'is_auto_get_feedback': self.is_ebay_auto_get_feedback,
            'order_auto_import': self.ebay_order_auto_import,
            'stock_auto_export': self.ebay_stock_auto_export,
            'ebay_order_auto_update': self.ebay_order_auto_update,
            'auto_update_payment': self.ebay_auto_update_payment or False,
            'auto_sync_active_products': self.ebay_auto_sync_active_products,
            'sync_active_products_start_date': self.ebay_sync_active_products_start_date,
        }
        if not self.ebay_auto_sync_active_products:
            values.update({'sync_active_products_start_date': False})
        seller.write(values)
        if self._context.get('is_calling_from_ebay_on_boarding_panel', False):
            if not seller:
                seller = self.ebay_seller_id
            if seller:
                action = self.env["ir.actions.actions"]._for_xml_id(
                    "ebay_ept.ebay_on_boarding_confirmation_wizard_action")
                action['context'] = {'ebay_seller_id': seller.id}
                return action
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def ebay_setup_get_feedback_cron(self, seller):
        """
        Set up eBay get feedback cron.
        :param seller: seller of eBay
        """
        if self.is_ebay_auto_get_feedback:
            cron_exist = self.check_cron_exist_or_not('ir_cron_get_feedback_', seller)
            get_ebay_feedback_int_type = self.get_ebay_feedback_interval_type
            get_ebay_feedback_int_number = self.get_ebay_feedback_interval_number
            seller_cron_values = self.prepare_seller_cron_values_dict(
                seller, get_ebay_feedback_int_number, get_ebay_feedback_int_type,
                self.get_ebay_feedback_user_id, 'auto_get_feedback')
            if cron_exist:
                seller_cron_values.update({'name': cron_exist.name})
                cron_exist.write(seller_cron_values)
            else:
                self.search_or_create_cron_or_raise_error(
                    'ir_cron_auto_get_feedback', seller, seller_cron_values, 'ir_cron_get_feedback_')
        else:
            cron_exist = self.check_cron_exist_or_not('ir_cron_get_feedback_', seller)
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def ebay_setup_order_import_cron(self, seller):
        """
        Set up eBay order import cron
        :param seller: current seller of eBay
        """
        if self.ebay_order_auto_import:
            cron_exist = self.check_cron_exist_or_not('ir_cron_send_ebay_import_sales_orders_seller_', seller)
            ebay_order_import_int_type = self.ebay_order_import_interval_type
            ebay_order_import_int_number = self.ebay_order_import_interval_number
            seller_cron_values = self.prepare_seller_cron_values_dict(
                seller, ebay_order_import_int_number, ebay_order_import_int_type,
                self.ebay_order_import_user_id, 'auto_import_ebay_sales_orders')
            if cron_exist:
                seller_cron_values.update({'name': cron_exist.name})
                cron_exist.write(seller_cron_values)
            else:
                self.search_or_create_cron_or_raise_error(
                    'ir_cron_send_ebay_import_sales_orders', seller,
                    seller_cron_values, 'ir_cron_send_ebay_import_sales_orders_seller_')
        else:
            cron_exist = self.check_cron_exist_or_not('ir_cron_send_ebay_import_sales_orders_seller_', seller)
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def ebay_setup_order_status_update_cron(self, seller):
        """
        Set up eBay order status update cron
        :param seller: seller of eBay
        """
        if self.ebay_order_auto_update:
            cron_exist = self.check_cron_exist_or_not('ir_cron_update_order_status_seller_', seller)
            ebay_order_update_int_type = self.ebay_order_update_interval_type
            ebay_order_update_int_number = self.ebay_order_update_interval_number
            seller_cron_values = self.prepare_seller_cron_values_dict(
                seller, ebay_order_update_int_number, ebay_order_update_int_type,
                self.ebay_order_status_update_user_id, 'auto_update_order_status')
            if cron_exist:
                seller_cron_values.update({'name': cron_exist.name})
                cron_exist.write(seller_cron_values)
            else:
                self.search_or_create_cron_or_raise_error(
                    'ir_cron_update_order_status', seller, seller_cron_values, 'ir_cron_update_order_status_seller_')
        else:
            cron_exist = self.check_cron_exist_or_not('ir_cron_update_order_status_seller_', seller)
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def ebay_setup_update_stock_cron(self, seller):
        """
        Set up eBay update stock cron
        :param seller: current instance of eBay
        """
        if self.ebay_stock_auto_export:
            cron_exist = self.check_cron_exist_or_not('ir_cron_auto_export_inventory_seller_', seller)
            ebay_update_stock_int_type = self.ebay_update_stock_interval_type
            ebay_update_stock_int_number = self.ebay_update_stock_interval_number
            seller_cron_values = self.prepare_seller_cron_values_dict(
                seller, ebay_update_stock_int_number, ebay_update_stock_int_type,
                self.ebay_stock_update_user_id, 'auto_export_inventory_ept')
            if cron_exist:
                seller_cron_values.update({'name': cron_exist.name})
                cron_exist.write(seller_cron_values)
            else:
                self.search_or_create_cron_or_raise_error(
                    'ir_cron_auto_export_inventory', seller,
                    seller_cron_values, 'ir_cron_auto_export_inventory_seller_')
        else:
            cron_exist = self.check_cron_exist_or_not('ir_cron_auto_export_inventory_seller_', seller)
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def ebay_setup_auto_sync_active_products(self, seller):
        """
        Set up auto sync products cron.
        :param seller: seller of eBay
        """
        if self.ebay_auto_sync_active_products:
            cron_exist = self.check_cron_exist_or_not('ir_cron_auto_sync_active_products_seller_', seller)
            sync_active_prod_int_type = self.ebay_sync_active_products_interval_type
            sync_active_prod_int_number = self.ebay_sync_active_products_interval_number
            seller_cron_values = self.prepare_seller_cron_values_dict(
                seller, sync_active_prod_int_number, sync_active_prod_int_type,
                self.ebay_sync_active_products_user_id, 'auto_sync_active_products_listings')
            if cron_exist:
                seller_cron_values.update({'name': cron_exist.name})
                cron_exist.write(seller_cron_values)
            else:
                self.search_or_create_cron_or_raise_error(
                    'ir_cron_auto_sync_active_products', seller,
                    seller_cron_values, 'ir_cron_auto_sync_active_products_seller_')
        else:
            cron_exist = self.check_cron_exist_or_not('ir_cron_auto_sync_active_products_seller_', seller)
            if cron_exist:
                cron_exist.write({'active': False})
        return True

    def search_or_create_cron_or_raise_error(self, cron_name, seller, seller_cron_values, cron_xml_name):
        """
        Search if cron is exist. If not exist, then raise User Error.
        If cron exist, then add new record of cron into ir.model.data
        :param cron_name: eBay cron name
        :param seller: eBay seller object
        :param seller_cron_values: dictionary of seller cron values
        :param cron_xml_name: Cron XML Id reference
        """
        try:
            seller_cron = self.env.ref('ebay_ept.%s' % cron_name)
        except Exception:
            seller_cron = False
        if not seller_cron:
            raise UserError(
                _('Core settings of eBay are deleted, please upgrade eBay Connector module to back this settings.'))
        name = seller.name + ' : ' + seller_cron.name
        seller_cron_values.update({'name': name})
        new_cron = seller_cron.copy(default=seller_cron_values)
        self.env['ir.model.data'].create({
            'module': 'ebay_ept',
            'name': '%s%d' % (cron_xml_name, seller.id),
            'model': 'ir.cron',
            'res_id': new_cron.id,
            'noupdate': True
        })

    @staticmethod
    def prepare_seller_cron_values_dict(seller, interval_number, interval_type, cron_user_id, cron_process_method_name):
        """
        Prepare dictionary for seller cron values.
        :param seller: eBay seller object
        :param interval_number: cron interval number
        :param interval_type: cron interval type
        :param cron_user_id: cron responsible user
        :param cron_process_method_name: Method name to process cron
        """
        next_cron_call = datetime.now()
        next_cron_call += _INTERVALTYPES[interval_type](interval_number)
        return {
            'active': True,
            'interval_number': interval_number,
            'interval_type': interval_type,
            'nextcall': next_cron_call.strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': cron_user_id and cron_user_id.id,
            'code': "model.%s({'seller_id':%d})" % (cron_process_method_name, seller.id),
            'ebay_seller_cron_id': seller.id
        }

    @api.model
    def action_ebay_cron_configuration_on_boarding_state(self):
        """
        Usage: Return the action for open the cron configuration wizard Called by on-boarding panel above the Instance.
        :return: True
        """
        action = self.env["ir.actions.actions"]._for_xml_id("ebay_ept.action_wizard_ebay_cron_configuration_ept")
        seller = self.env['ebay.seller.ept'].search_ebay_seller()
        action['context'] = {'is_calling_from_ebay_on_boarding_panel': True}
        if seller:
            action.get('context').update({'default_ebay_seller_id': seller.id,
                                          'is_instance_exists': True})
        return action
