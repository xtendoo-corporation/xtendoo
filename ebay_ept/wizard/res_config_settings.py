#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes configuration for eBay seller and sites.
"""
from werkzeug import urls
import uuid

from odoo import models, fields, api
from odoo.http import request
from odoo.addons.ebay_ept.controllers.webhook import Webhook


class ResConfigSettings(models.TransientModel):
    """
    Describes eBay Configurations
    """
    _inherit = 'res.config.settings'

    ebay_seller_id = fields.Many2one('ebay.seller.ept', 'Seller', help="Select eBay seller.")
    ebay_instance_id = fields.Many2one('ebay.instance.ept', 'eBay Instances', help="Select eBay Site.")
    ebay_warehouse_id = fields.Many2one('stock.warehouse', string="eBay Warehouse", help="eBay Warehouse")
    ebay_country_id = fields.Many2one('res.country', string="Country", help="eBay Site Country")
    ebay_lang_id = fields.Many2one('res.lang', string='Language', help="eBay site Language")
    ebay_order_prefix = fields.Char(size=10, string='eBay Order Prefix', help="Set the eBay order prefix name")
    fiscal_position_id = fields.Many2one('account.fiscal.position',
                                         string='Fiscal Position')  # Added by Tushal Nimavat on 23/06/2022
    ebay_order_import_days = fields.Char(
        size=10, string='eBay Order Import Before', default="3",
        help="Set number of days to import sale orders from last import date.")
    ebay_stock_field = fields.Selection([
        ('free_qty', 'Free Quantity'), ('virtual_available', 'Forecast Quantity')
    ], string="eBay Stock Type", default='free_qty', help="eBay Stock Type")
    ebay_email_add = fields.Char('Paypal Email ID', size=126, help="Seller paypal email id")
    ebay_pricelist_id = fields.Many2one('product.pricelist', string='eBay Pricelist')
    ebay_shipment_charge_product_id = fields.Many2one(
        "product.product", string="eBay Shipment Fee", help="Set eBay Shipment Fee", domain=[('type', '=', 'service')])
    ebay_create_new_product = fields.Boolean(
        string="eBay Auto Create New Product ?", default=False,
        help="If checked, it will automatically create new product in odoo when product SKU not found")
    ebay_team_id = fields.Many2one('crm.team', string='eBay Sales Team', help='Set eBay Sales Team')
    ebay_post_code = fields.Char(string='eBay Postal Code', size=64, help="Enter the Postal Code for Item Location")
    ebay_discount_charge_product_id = fields.Many2one(
        "product.product", string="eBay Order Discount", help="Set eBay Order Discount",
        domain=[('type', '=', 'service')])
    ebay_plus = fields.Boolean(
        string="Is eBay Plus Account ?", default=False, help="If checked, seller uses eBay plus account")
    ebay_use_dynamic_desc = fields.Boolean(
        string="eBay Use Dynamic Description Template ?",
        help='If ticked then you can able to use dynamic product description for an individual product only.')
    ebay_item_location_country = fields.Many2one(
        "ebay.site.details", string="eBay Item Location(Country)", help="Select the country for the Item Location.")
    ebay_item_location_name = fields.Char(
        string="eBay Item Location(City, State) Name", help="Item Location(City, State) name.")
    # Account Field
    ebay_property_account_payable_id = fields.Many2one(
        'account.account', string="eBay Accounts Payable",
        domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False)]",
        help='This account will be used instead of the default one as the payable account for the current partner')
    ebay_property_account_receivable_id = fields.Many2one(
        'account.account', string="eBay Accounts Receivable",
        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False)]",
        help='This account will be used instead of the default one as the receivable account for the current partner')
    ebay_is_use_default_sequence = fields.Boolean(
        "Use Odoo Default Sequence in eBay Orders?",
        help="If checked,Then use default sequence of odoo while create sale order imported from eBay.")
    ebay_auto_update_payment = fields.Boolean(string="eBay Auto Update Payment On Invoice Paid ?")
    ebay_stock_warehouse_ids = fields.Many2many(
        "stock.warehouse",
        'ebay_instance_config_export_stock_warehouse_rel',
        'warehouse_id', 'instance_id',
        string="Select Export Stock Warehouse", help="eBay export stock Warehouse")
    ebay_is_create_delivery_carrier = fields.Boolean(
        string="Is eBay Delivery Carrier Create?",
        help="If checked, then create delivery carrier in case not found when import sale order from eBay")
    ebay_is_sync_stock = fields.Boolean(
        "Is product stock synced?", default=False, help="Is product stock synced when Sync/import products?")
    ebay_is_sync_price = fields.Boolean(
        "Is product price synced?", default=False, help="Is product price synced when Sync/import products?")

    ebay_deletion_token_ept = fields.Char(config_parameter="ebay_ept.ebay_deletion_token_ept", readonly=True)
    ebay_deletion_endpoint_ept = fields.Char(compute="_compute_ebay_deletion_endpoint_ept")


    def generate_ebay_token(self):
        """
        Generates new token for the account deletion notification.
        @author: Maulik Barad on Date 20-Jul-2022.
        """
        self.env['ir.config_parameter'].set_param("ebay_ept.ebay_deletion_token_ept", uuid.uuid4())
        return True

    @api.depends("company_id")
    def _compute_ebay_deletion_endpoint_ept(self):
        """
        Computes the Marketplace account deletion notification endpoint.
        @author: Maulik Barad on Date 20-Jul-2022.
        """
        for wizard in self:
            wizard.ebay_deletion_endpoint_ept = urls.url_join(
                self.env['ir.config_parameter'].sudo().get_param("web.base.url"), Webhook._endpoint)

    @api.onchange('ebay_seller_id')
    def onchange_ebay_seller_id(self):
        """
        Sets default values for configuration when change/ select eBay seller.
        """
        values = {}
        domain = {}
        if self.ebay_seller_id:
            request.session['ebay_seller_id'] = self.ebay_seller_id.id
            seller = self.env['ebay.seller.ept'].browse(self.ebay_seller_id.id)
            values = self.onchange_ebay_instance_id()
            values['value']['ebay_instance_id'] = False
            values['value']['ebay_email_add'] = seller.email_add
            values['value']['ebay_shipment_charge_product_id'] = False
            if seller.shipment_charge_product_id:
                values['value']['ebay_shipment_charge_product_id'] = seller.shipment_charge_product_id.id
            values['value']['ebay_discount_charge_product_id'] = False
            if seller.discount_charge_product_id:
                values['value']['ebay_discount_charge_product_id'] = seller.discount_charge_product_id.id
            values['value']['ebay_plus'] = seller.ebay_plus
            values['value']['ebay_use_dynamic_desc'] = seller.use_dynamic_desc
            values['value']['ebay_order_prefix'] = seller.order_prefix
            values['value']['ebay_is_use_default_sequence'] = seller.ebay_is_use_default_sequence
            values['value']['order_import_days'] = seller.order_import_days
            values['value']['ebay_team_id'] = False
            if seller.ebay_team_id:
                values['value']['ebay_team_id'] = seller.ebay_team_id.id
            values['value']['ebay_create_new_product'] = seller.create_new_product
            values['value']['ebay_auto_update_payment'] = seller.auto_update_payment
            values['value']['ebay_is_create_delivery_carrier'] = seller.ebay_is_create_delivery_carrier
            values['value']['ebay_is_sync_stock'] = seller.ebay_is_sync_stock
            values['value']['ebay_is_sync_price'] = seller.ebay_is_sync_price
        else:
            values.update({'value': {'ebay_instance_id': False}})
        values.update({'domain': domain})
        return values

    def create_more_ebay_sites(self):
        """
        Create Other eBay Site instance in ERP.
        :return:
        """
        action = self.env.ref('ebay_ept.res_config_action_ebay_site', False)
        result = {}
        if action and action.read()[0]:
            result = action.read()[0]
        ctx = result.get('context', {}) and eval(result.get('context'))
        ctx.update({'default_seller_id': request.session['ebay_seller_id']})
        result['context'] = ctx
        return result

    @api.onchange('ebay_instance_id')
    def onchange_ebay_instance_id(self):
        """
        set some eBay configurations based on changed eBay instance.
        """
        vals = {}
        instance = self.ebay_instance_id
        if instance:
            vals['ebay_warehouse_id'] = self.env['stock.warehouse'].search([
                ('company_id', '=', self.env.company.id)], limit=1).id
            if instance.warehouse_id:
                vals['ebay_warehouse_id'] = instance.warehouse_id.id
            if instance.ebay_stock_warehouse_ids:
                vals['ebay_stock_warehouse_ids'] = instance.ebay_stock_warehouse_ids.ids
            vals['ebay_lang_id'] = self.env['res.lang'].search([('code', '=', 'en_US')]).id
            if instance.lang_id:
                vals['ebay_lang_id'] = instance.lang_id.id
            vals['ebay_stock_field'] = instance.ebay_stock_field
            vals['ebay_pricelist_id'] = False
            if instance.pricelist_id:
                vals['ebay_pricelist_id'] = instance.pricelist_id.id
            vals['fiscal_position_id'] = instance.fiscal_position_id  # Added by Tushal Nimavat on 23/06/2022
            vals['ebay_post_code'] = instance.post_code or False
            vals['ebay_property_account_payable_id'] = False
            if instance.ebay_property_account_payable_id:
                vals['ebay_property_account_payable_id'] = instance.ebay_property_account_payable_id.id
            vals['ebay_property_account_receivable_id'] = False
            if instance.ebay_property_account_receivable_id:
                vals['ebay_property_account_receivable_id'] = instance.ebay_property_account_receivable_id.id
            vals['ebay_item_location_country'] = self.ebay_instance_id.site_id.id
            if instance.site_id:
                vals['ebay_item_location_country'] = instance.site_id.id
            vals['ebay_country_id'] = instance.country_id.id
            if self.ebay_country_id.id:
                vals['ebay_country_id'] = instance.country_id.id
            vals['ebay_item_location_name'] = instance.item_location_name or ''
        return {'value': vals}

    def execute(self):
        """
        Save all selected eBay configurations
        """
        instance = self.ebay_instance_id or False
        res = super(ResConfigSettings, self).execute()
        if instance:
            ebay_warehouse_id = False
            if self.ebay_warehouse_id:
                ebay_warehouse_id = self.ebay_warehouse_id.id
            ebay_stock_warehouse_ids = False
            if self.ebay_stock_warehouse_ids:
                ebay_stock_warehouse_ids = self.ebay_stock_warehouse_ids.ids
            ebay_lang_id = False
            if self.ebay_lang_id:
                ebay_lang_id = self.ebay_lang_id.id
            ebay_pricelist_id = False
            if self.ebay_pricelist_id:
                ebay_pricelist_id = self.ebay_pricelist_id.id
            ebay_item_loc_country = False
            if self.ebay_item_location_country:
                ebay_item_loc_country = self.ebay_item_location_country.id
            country_id = False
            if self.ebay_country_id:
                country_id = self.ebay_country_id.id
            # Account Field
            ebay_property_account_receivable_id = False
            if self.ebay_property_account_receivable_id:
                ebay_property_account_receivable_id = self.ebay_property_account_receivable_id.id
            ebay_property_account_payable_id = False
            if self.ebay_property_account_payable_id:
                ebay_property_account_payable_id = self.ebay_property_account_payable_id.id
            ebay_instance_values = {
                'warehouse_id': ebay_warehouse_id, 'lang_id': ebay_lang_id,
                'pricelist_id': ebay_pricelist_id, 'post_code': self.ebay_post_code or False,
                'fiscal_position_id': self.fiscal_position_id,  # Added by Tushal Nimavat on 23/06/2022
                'ebay_stock_field': self.ebay_stock_field,
                'country_id': country_id, 'item_location_name': self.ebay_item_location_name or '',
                'ebay_property_account_receivable_id': ebay_property_account_receivable_id,
                'ebay_property_account_payable_id': ebay_property_account_payable_id,
                'ebay_stock_warehouse_ids': ebay_stock_warehouse_ids}
            instance.write(ebay_instance_values)
        if self.ebay_seller_id:
            shipment_charge_product_id = False
            if self.ebay_shipment_charge_product_id:
                shipment_charge_product_id = self.ebay_shipment_charge_product_id.id
            discount_charge_product_id = False
            if self.ebay_discount_charge_product_id:
                discount_charge_product_id = self.ebay_discount_charge_product_id.id
            ebay_team_id = False
            if self.ebay_team_id:
                ebay_team_id = self.ebay_team_id.id
            ebay_seller_values = {
                'ebay_plus': self.ebay_plus, 'shipment_charge_product_id': shipment_charge_product_id,
                'discount_charge_product_id': discount_charge_product_id,
                'use_dynamic_desc': self.ebay_use_dynamic_desc, 'email_add': self.ebay_email_add,
                'order_prefix': self.ebay_order_prefix or '',
                'ebay_is_use_default_sequence': self.ebay_is_use_default_sequence, 'ebay_team_id': ebay_team_id,
                'create_new_product': self.ebay_create_new_product, 'order_import_days': self.ebay_order_import_days,
                'auto_update_payment': self.ebay_auto_update_payment,
                'ebay_is_create_delivery_carrier': self.ebay_is_create_delivery_carrier,
                'ebay_is_sync_stock': self.ebay_is_sync_stock,
                'ebay_is_sync_price': self.ebay_is_sync_price,
            }
            self.ebay_seller_id.write(ebay_seller_values)
        return res
