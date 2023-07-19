#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods to store sale order line for imported eBay orders.
"""
import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    """
    Describes eBay Sales Order Line
    """
    _inherit = 'sale.order.line'
    ebay_order_line_item_id = fields.Char(string="eBay Order Item Id")
    ebay_instance_id = fields.Many2one(
        "ebay.instance.ept", string="eBay Instance", related="order_id.ebay_instance_id", readonly=True,
        help="eBay Site")
    ebay_seller_id = fields.Many2one("ebay.seller.ept", "Seller", help="eBay Seller")
    item_id = fields.Char("Order Item Id")
    seller_discount_campaign_display_name = fields.Char('Campaign Display Name')
    seller_discount_campaign_id = fields.Integer('Campaign Id')
    line_tax_amount = fields.Float("Line Tax", default=0.0, digits="Product Price",
                                   help="Order line tax amount")

    def create_ebay_products(self, odoo_product, instance):
        """
        Creates eBay product
        :param odoo_product:  Odoo product Object
        :param instance: instance of eBay
        """
        ebay_product_listing_obj = self.env['ebay.product.listing.ept']
        product_template = odoo_product.product_tmpl_id
        order_line_product = False
        ebay_template = ebay_product_listing_obj.search_or_create_ebay_product_template(
            product_template.id, instance.id, product_template.name, product_template.description_sale)
        product_variant_ids = product_template.product_variant_ids
        for variant in product_variant_ids:
            ebay_variant = ebay_product_listing_obj.search_ebay_product_by_product_id(variant.id, instance.id)
            if not ebay_variant:
                ebay_variant = ebay_product_listing_obj.create_ebay_product(
                    variant, ebay_template.id, instance.id, '')
                if not order_line_product and odoo_product.default_code == variant.default_code:
                    order_line_product = ebay_variant
        return order_line_product

    def create_ebay_sale_order_line(self, order_response, instance, sale_order, order_queue):
        """
        Creates eBay Sale Order Line.
        :param order_response: response of eBay sale order
        :param instance: current instance of eBay
        :param ebay_order: ebay order object
        """
        log_line_obj = self.env["common.log.lines.ept"]
        ebay_product_listing_obj = self.env['ebay.product.listing.ept']
        transaction_array = order_response.get('TransactionArray', False)
        order_lines = transaction_array and order_response['TransactionArray'].get('Transaction', [])
        odoo_product = False
        sale_order_lines = []
        if isinstance(order_lines, dict):
            order_lines = [order_lines]
        for order_line_dict in order_lines:
            sku = order_line_dict.get('Variation', {}).get('SKU', False)
            item_id = order_line_dict.get('Item', {}).get('ItemID', {})
            if not sku:
                sku = order_line_dict.get('Item', {}).get('SKU', False)
            if not sku:
                listing_record = ebay_product_listing_obj.search_product_listing_by_name(item_id, instance.id)
                if listing_record:
                    odoo_product = listing_record.ebay_variant_id.product_id
            else:
                ebay_product = ebay_product_listing_obj.search_ebay_product_by_sku(sku, instance.id)
                if not ebay_product:
                    odoo_product = ebay_product_listing_obj.search_odoo_product_by_sku(sku)
                else:
                    odoo_product = ebay_product.product_id
            if not odoo_product:
                message = "Skip order due to not found the active listing for item id: %s and order Id: %s" % (
                    item_id, order_response.get('OrderID'))
                _logger.info(message)
                log_line = log_line_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                                   model_name='sale.order.line',
                                                                   log_line_type='fail', mismatch=True,
                                                                   ebay_instance_id=instance.id)
                log_line.write({'ebay_order_data_queue_line_id': order_queue.id})
                sale_order.unlink()
                return False
            price_unit = self.get_ebay_item_price(order_line_dict)
            order_line_values = self.create_sale_order_line_values(order_line_dict, price_unit, odoo_product,
                                                                   sale_order, instance)
            sale_line = self.create(order_line_values)
            sale_order_lines.append(sale_line)
            # pass order_response in the below method for take shipping cost from 'MultiLegShippingDetails' tag when order has 'MultiLegShippingDetails'.
            shipping_costs = self.get_ebay_shipping_price(order_line_dict, order_response)

            if shipping_costs > 0.0:
                line = self.create_shipping_product_order_line(order_line_dict, sale_order, instance, shipping_costs)
                sale_order_lines.append(line)
        return sale_order_lines

    def create_sale_order_line_values(self, order_line_dict, price_unit, odoo_product=False, sale_order=False,
                                      instance=False, is_shipping=False):
        """
        Create Sale Order Line Values
        :param order_line_dict:  ebay sale order line object
        :param price_unit: price unit object
        :param odoo_product: odoo product object
        :param sale_order: sale order object
        :param instance: current instance of ebay
        :return:
        """
        order_qty = 1.0 if is_shipping else float(order_line_dict.get('QuantityPurchased', 1.0))
        uom_id = odoo_product.uom_id.id
        if is_shipping:
            item_tax = self.get_ebay_shipping_tax_amount(order_line_dict)
        else:
            item_tax = self.get_ebay_item_tax_amount(order_line_dict)
        order_line_values = {
            'order_id': sale_order.id,
            'product_id': odoo_product and odoo_product.id or False,
            'company_id': sale_order.company_id.id,
            'name': odoo_product.name,
            'product_uom': uom_id,
            'product_uom_qty': order_qty,
            'price_unit': price_unit,
        }
        # order_line_values = self.create_sale_order_line_ept(order_line_values)
        order_line_values.update({
            'ebay_instance_id': instance.id,
            'ebay_order_line_item_id': order_line_dict.get('OrderLineItemID', {}),
            'item_id': order_line_dict.get('Item', {}).get('ItemID', False),
        })
        if item_tax:
            order_line_values.update({'line_tax_amount': item_tax / order_qty})
        return order_line_values

    def get_ebay_item_price(self, order_line_dict):
        """
        Get Item Price including tax into order line items.
        :param order_line_dict: Order line item received from eBay.
        :return: item price with tax.
        Migration done by Haresh Mori @ Emipro on date 10 January 2022 .
        """
        transaction_price = order_line_dict.get('TransactionPrice', False)
        item_price = transaction_price and order_line_dict['TransactionPrice'].get('value', 0.0)
        tax_amount = self.get_ebay_item_tax_amount(order_line_dict)
        return tax_amount + float(item_price)

    def get_ebay_shipping_price(self, order_line_dict, order_response):
        """
        Get Item Price including tax into order line items.
        :param order: sale order object.
        :param order_line_dict: Order line item received from eBay.
        :return: item price with tax.

        Added MultiLegShippingDetails related condtion. when in order has MultiLegShippingDetails then take shipping cost from MultiLegShippingDetails tag.
        Task : 171947 , @last_update_on : 10/03/2021
        """
        shipping_costs = float(order_line_dict.get('ActualShippingCost', {}).get('value', 0.0))
        if order_response.get('IsMultiLegShipping').lower() == 'true' and order_response.get('MultiLegShippingDetails'):
            shipping_costs = float(
                order_response.get('MultiLegShippingDetails', {}).get('SellerShipmentToLogisticsProvider', {}).get(
                    'ShippingServiceDetails', {}).get('TotalShippingCost', {}).get('value', 0.0))

        tax_amount = self.get_ebay_shipping_tax_amount(order_line_dict)
        return tax_amount + shipping_costs

    def get_ebay_item_tax_amount(self, order_line_dict):
        """
        Get Item Tax of order item.
        :param order_line_dict: Order line item received from eBay.
        :return: item tax
        Migration done by Haresh Mori @ Emipro on date 10 January 2022 .
        """
        ebay_order_taxes = order_line_dict.get('Taxes')
        tax_amount = ebay_order_taxes and float(
            order_line_dict['Taxes'].get('TaxDetails', {}).get('TaxOnSubtotalAmount', {}).get('value', 0.0))
        return tax_amount

    def get_ebay_shipping_tax_amount(self, order_line_dict):
        """
        Get Item Tax of order item.
        :param order_line_dict: Order line item received from eBay.
        :return: item tax
        Migration done by Haresh Mori @ Emipro on date 10 January 2022 .
        """
        ebay_order_taxes = order_line_dict.get('Taxes')
        tax_amount = ebay_order_taxes and float(
            order_line_dict['Taxes'].get('TaxDetails', {}).get('TaxOnShippingAmount', {}).get('value', 0.0))
        return tax_amount

    def create_shipping_product_order_line(self, order_line_dict, sale_order, instance, shipping_cost):
        """
        Create Shipping product order line.
        :param ebay_order: Sale order object
        :param instance: eBay instance object
        :param shipping_cost: Shipping charge
        Migration done by Haresh Mori @ Emipro on date 10 January 2022 .
        """
        shipment_charge_product = instance.seller_id.shipment_charge_product_id
        order_line_values = self.create_sale_order_line_values(
            order_line_dict, shipping_cost, shipment_charge_product, sale_order, instance, True)
        order_line_values.update({'is_delivery': True})
        sale_line = self.create(order_line_values)
        return sale_line

    def create_discount_product_order_line(self, sale_order, instance, discount_values, order_discount):
        """
        Create discount product order line.
        :param sale_order: Sale order object
        :param instance: eBay instance object.
        :param discount_values: Discount charge
        :param order_discount: Order discount response received from eBay.
        Migration done by Haresh Mori @ Emipro on date 10 January 2022 .
        """
        discount_charge_product = instance.seller_id.discount_charge_product_id
        campaign_display_name = order_discount.get('CampaignDisplayName').get('value')
        discount_campaign_id = order_discount.get('CampaignID').get('value')
        order_line_values = self.create_sale_order_line_vals({}, -discount_values, discount_charge_product, sale_order,
                                                             instance)
        order_line_values.update({
            'seller_discount_campaign_display_name': campaign_display_name,
            'seller_discount_campaign_id': discount_campaign_id})
        self.create(order_line_values)
