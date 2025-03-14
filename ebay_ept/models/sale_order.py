#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for import and store sale order from eBay to Odoo.
"""
import json
import logging
from datetime import datetime
from odoo import models, fields, _
from odoo.tools.misc import split_every
from odoo.exceptions import UserError, RedirectWarning, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """
    Import Sale order from eBay and update status
    """
    _inherit = "sale.order"

    feedback_ids = fields.One2many("ebay.feedback.ept", "sale_order_id", string='ebay Feedback', help="eBay Feedbacks")
    ebay_order_id = fields.Char(
        size=350, string='eBay Order Ref', required=False, index=True,
        help="Unique Order Reference received from eBay Order")
    selling_manager_sales_record_number = fields.Char(copy=False)
    ebay_instance_id = fields.Many2one("ebay.instance.ept", string="Site", index=True, help="eBay Site")
    ebay_seller_id = fields.Many2one("ebay.seller.ept", string="Seller", help="eBay Seller")
    shipping_id = fields.Many2one('ebay.shipping.service', string='Shipping', help="eBay Shipping service")
    updated_in_ebay = fields.Boolean(
        string='Updated in eBay', search="_search_ebay_order_ids", compute="_compute_get_ebay_status",
        store=False, help="Order is updated in eBay or not")
    ebay_payment_option_id = fields.Many2one(
        'ebay.payment.options', string="Payment Option", help="eBay Payment Option")
    ebay_buyer_id = fields.Char(
        string="Buyer Id", default=False, copy=False, help="Unique identification number of eBay Buyer")
    is_ebay_remit_tax = fields.Boolean(
        string="Is eBay remit Tax?", default=False, copy=False,
        help="True. It means eBay is responsible for the tax in order.")

    ebay_site_id = fields.Many2one('ebay.site.details', string='eBay Site', help="eBay Sites")
    _sql_constraints = [('_ebay_sale_order_unique_constraint', 'unique(ebay_order_id,ebay_seller_id, ebay_instance_id)',
                         "eBay order must be unique")]

    def _search_ebay_order_ids(self, operator, value):
        """
        Search ebay orders ids
        :return: dictionary of searched ebay order ids
        """
        query = """
                   select sale_order.id from stock_picking
                   inner join sale_order on sale_order.procurement_group_id=stock_picking.group_id 
                   and sale_order.ebay_order_id is not null
                   inner join stock_location on stock_location.id=stock_picking.location_dest_id 
                   and (stock_location.usage='customer')
                   where stock_picking.updated_in_ebay=%s and stock_picking.state=%s    
                 """
        self._cr.execute(query, (False, 'done'))
        results = self._cr.fetchall()
        order_ids = []
        for result_tuple in results:
            order_ids.append(result_tuple[0])
        return [('id', 'in', order_ids)]

    def _compute_get_ebay_status(self):
        """
        Check order is updated in ebay or not.
        """
        for order in self:
            if order.picking_ids:
                order.updated_in_ebay = True
            else:
                order.updated_in_ebay = False
            for picking in order.picking_ids:
                if picking.state == 'cancel' or picking.picking_type_id.code != 'outgoing':
                    continue
                if not picking.updated_in_ebay:
                    order.updated_in_ebay = False
                    break

    def _prepare_invoice(self):
        """
        We need to Inherit this method to set eBay instance,
        seller, payment option and global channel id in Invoice
        :return: dictionary to prepare invoice
        """
        res = super(SaleOrder, self)._prepare_invoice()
        res.update({
            'ebay_seller_id': self.ebay_instance_id and self.ebay_instance_id.seller_id.id or False,
            'ebay_instance_id': self.ebay_instance_id and self.ebay_instance_id.id or False,
            'ebay_payment_option_id': self.ebay_payment_option_id.id,
        })
        return res

    def get_ebay_order_site(self, order_dict):
        """
        Get eBay site for particular order
        :param order_dict: order dictionary received from eBay API
        :return: ebay site details object
        Migration done by Haresh Mori @ Emipro on date 6 January 2022 .
        """
        transaction_array = order_dict['TransactionArray'].get('Transaction', False)
        order_transaction = order_dict['TransactionArray']['Transaction']
        transaction = order_dict.get('TransactionArray', False) and transaction_array and order_transaction or {}
        if isinstance(transaction, list):
            transaction = transaction[0]
        site = ''
        if transaction.get('Item', False):
            site = transaction['Item'].get('Site', False)
            _logger.info("Site name: %s receive in order response:" % site)
        return self.env['ebay.site.details'].search([('name', '=', site)], limit=1)

    def check_payment_and_products_of_order(self, order_data_queue_line_id, order_dict, instance, log_book_id,
                                            ebay_pr_sku):
        """
        Check Payment method, payment term and create/ update product
        :param order_data_queue_line_id: order data queue line id
        :param order_dict: order dictionary received from eBay API
        :param instance: instance of eBay
        :param log_book_id: common log book object or False
        :param ebay_pr_sku: ebay product dictionary
        :return: skip order, is ebay mismatch and job
        """
        order_ref = order_dict['OrderID']
        order_checkout_status = order_dict['CheckoutStatus']
        payment_stat = order_checkout_status['eBayPaymentStatus']
        skip_order = False
        common_log_lines_ept_obj = self.env['common.log.lines.ept']
        payment_method = order_checkout_status['PaymentMethod']
        payment_option = self.get_payment_option_and_method(instance, order_dict)
        message = ''
        if payment_stat in ('BuyerCreditCardFailed', 'BuyerECheckBounced'):
            skip_order = True
            message = _("Order %s skipped due to Payment Status is %s", order_ref, payment_stat)
        elif not payment_option:
            skip_order = True
            message = _("Order %s skipped due to auto workflow configuration not found for payment method %s",
                        order_ref, payment_method)
        elif payment_option and not payment_option.payment_term_id:
            skip_order = True
            message = _("Order %s skipped due to Payment Term not found in payment method %s",
                        order_ref, payment_method)
        if skip_order:
            find_common_message = common_log_lines_ept_obj.search([('message', '=ilike', message)])
            if not find_common_message:
                log_book_id.create_order_common_log_lines(message, order_ref, order_data_queue_line_id)
            return skip_order
        skip_order = self.get_ebay_shipping_details(
            order_dict, instance.seller_id, log_book_id, order_data_queue_line_id)
        if skip_order:
            return skip_order
        transaction_array = order_dict.get('TransactionArray', False)
        order_lines = transaction_array and transaction_array.get('Transaction', [])
        skip_order = self.create_or_update_product(order_lines, instance, ebay_pr_sku, order_ref,
                                                   order_data_queue_line_id, log_book_id)
        return skip_order

    def create_or_update_product(self, order_lines, instance, ebay_pr_sku, order_ref, order_data_queue_line_id,
                                 log_book_id):
        """
        If odoo product founds and ebay product not found then no need to check anything
        and create new ebay product, if odoo product not found then
        go to check configuration which action has to be taken for that.

        There are following situations managed by code.
        In any situation log that event and action.

        1). eBay product and Odoo product not found
            => Check seller configuration if allow to create new product then create product.
            => Enter log details with action.
        2). eBay product not found but odoo product is there.
            => Created eBay product with log and action.
        :param order_lines: order lines received from eBay API
        :param instance: instance of eBay
        :param ebay_pr_sku: eBay product dictionary
        :param order_ref: order reference
        :param order_data_queue_line_id: order data queue line id
        :param log_book_id: common log book object
        :return: skip order
        """
        skip_order = False
        if isinstance(order_lines, dict):
            order_lines = [order_lines]
        for order_line in order_lines:
            ebay_sku = order_line.get('Variation', {}).get('SKU', False)
            if not ebay_sku:
                ebay_sku = order_line.get('Item', {}).get('SKU', False)
            if not ebay_sku:
                item_id = order_line.get('Item', {}).get('ItemID', {})
                listing_record = self.env['ebay.product.listing.ept'].search_product_listing_by_name(
                    item_id, instance.id)
                if not listing_record:
                    ebay_sku = self.env['ebay.product.product.ept'].get_ebay_item_listing(instance, item_id)
                else:
                    ebay_variant_id = listing_record.ebay_variant_id
                    ebay_sku = ebay_variant_id and ebay_variant_id.ebay_sku
            if not ebay_pr_sku or (
                    ebay_pr_sku and (instance.id not in ebay_pr_sku.keys() or
                                     (instance.id in ebay_pr_sku.keys()
                                      and ebay_sku not in ebay_pr_sku[instance.id].keys()))):
                ebay_product, skip_order = self.search_or_create_ebay_product(
                    instance, ebay_sku, order_line, log_book_id, order_ref, order_data_queue_line_id, skip_order)
                if not skip_order:
                    if ebay_pr_sku and instance.id in ebay_pr_sku.keys():
                        ebay_pr_sku[instance.id][ebay_sku] = ebay_product.product_id.id
                    else:
                        ebay_pr_sku.update({instance.id: {ebay_sku: ebay_product.product_id.id}})
        return skip_order

    def search_or_create_ebay_product(
            self, instance, ebay_sku, order_line, log_book_id, order_ref, order_data_queue_line_id, skip_order):
        """
        Search eBay product. if not found then create eBay product.
        :param instance: eBay instance object
        :param ebay_sku: sku received from eBay.
        :param order_line: order item received from eBay.
        :param log_book_id: common log book object
        :param order_ref: eBay order reference
        :param order_data_queue_line_id: order data queue line id
        :param skip_order: True if any error else False
        :return: eBay product product object and skip_order
        """
        sale_order_line_obj = self.env['sale.order.line']
        ebay_product_listing_obj = self.env['ebay.product.listing.ept']
        common_log_lines_ept_obj = self.env['common.log.lines.ept']
        ebay_product = False
        create_new_product = instance.seller_id.create_new_product
        if ebay_sku:
            ebay_product = ebay_product_listing_obj.search_ebay_product_by_sku(ebay_sku, instance.id)
        else:
            skip_order = True
            message = _('Product SKU null found for %s instance', instance.name)
        if ebay_product and not ebay_product.product_id:
            odoo_product, message, skip_order = self.search_or_create_odoo_product(
                order_line, ebay_sku, create_new_product, skip_order, instance)
            if odoo_product:
                ebay_product.write({'product_id': odoo_product.id})
        if not ebay_product:
            odoo_product, message, skip_order = self.search_or_create_odoo_product(
                order_line, ebay_sku, create_new_product, skip_order, instance)
            if odoo_product and not skip_order:
                ebay_product = sale_order_line_obj.create_ebay_products(odoo_product, instance)
        if skip_order:
            find_common_message = common_log_lines_ept_obj.search([('message', '=ilike', message)])
            if not find_common_message:
                log_book_id.create_order_common_log_lines(message, order_ref, order_data_queue_line_id)
        return ebay_product, skip_order

    def search_or_create_odoo_product(
            self, order_line, ebay_sku, create_new_product, skip_order, instance):
        """
        Search or create Odoo product if it is not exist.
        :param order_line: Order item received from eBay.
        :param ebay_sku: eBay sku
        :param create_new_product: If True, Product will be created when not found in Odoo.
        :param skip_order: True if any error else False
        :param instance: eBay instance object
        :return: product product object, skip_order, message
        """
        ebay_product_listing_obj = self.env['ebay.product.listing.ept']
        message = ""
        odoo_product = ebay_product_listing_obj.search_odoo_product_by_sku(ebay_sku)
        if not odoo_product and not create_new_product:
            skip_order = True
            message = _('Product %s not found for %s instance', ebay_sku, instance.name)
        elif not odoo_product and create_new_product:
            title = order_line.get('VariationTitle')
            if not title:
                title = order_line.get('Item', {}).get('Title', False)
            odoo_product = ebay_product_listing_obj.create_odoo_product(title, ebay_sku)
        return odoo_product, message, skip_order

    @staticmethod
    def get_payment_option_and_method(instance, order_response):
        """
        Get payment option and payment method from order response.
        :param instance: ebay instance object
        :param order_response: order response received from eBay.
        :return: payment method, payment option
        Migration done by Haresh Mori @ Emipro on date 8 January 2022 .
        """
        payment_method = order_response['CheckoutStatus']['PaymentMethod']
        payment_option = instance.seller_id.payment_option_ids.filtered(
            lambda x: x.name == payment_method and x.auto_workflow_id)
        return payment_option

    def create_ebay_sales_order_ept(self, seller, order_queue_line, order_queue):
        """
        This method is use to create sale order.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 10 January 2022 .
        Task_id: 180140 - Import Unshipped Orders
        """
        log_lines_obj = self.env['common.log.lines.ept']
        res_partner_obj = self.env['res.partner']
        sale_order = False
        order_response = json.loads(order_queue_line.order_data)
        order_ref = order_response['OrderID']
        _logger.info("Processing order id: %s" % order_ref)
        existing_order = self.search([('ebay_order_id', '=', order_ref), ('ebay_seller_id', '=', seller.id)])
        if existing_order:
            _logger.info(
                "Processing order id: %s and found the existing order in odoo: %s" % (order_ref, existing_order.name))
            order_queue_line.write(
                {'state': 'done', 'processed_at': datetime.now(), 'sale_order_id': existing_order.id})
            return True
        ebay_site = self.get_ebay_order_site(order_response)
        instance = seller.instance_ids.filtered(lambda x: x.site_id == ebay_site)
        if instance:
            skip_order = self.ebay_check_mismatch_details_for_order(instance, order_response, order_queue_line)
            if skip_order:
                return False
            partner, shipping_partner = res_partner_obj.create_or_update_ebay_partner(order_response, instance)
            _logger.info("Partner: %s and shipping partner: %s for ebay order reference: %s " % (
                partner.name, shipping_partner.name, order_ref))

            is_ebay_remit_tax = self.check_order_is_ebay_remit_tax(order_response)

            # Create Sale Order
            order_values = self.create_ebay_sales_order_values(partner, shipping_partner, order_response, instance)
            order_values.update({'is_ebay_remit_tax': is_ebay_remit_tax})
            if instance.fiscal_position_id:
                order_values.update(
                    {'fiscal_position_id': instance.fiscal_position_id.id})  # Added by Tushal Nimavat on 23/06/2022
            sale_order = self.create(order_values)
            _logger.info("Created sale order: %s and creating sale order line" % sale_order.name)
            order_lines = self.create_ebay_sale_order_lines(order_response, instance, sale_order, order_queue)
            if not order_lines:
                return False

            self.ebay_process_auto_invoice_workflow(sale_order, instance, order_response, order_queue_line, order_queue)

            if not sale_order.order_line:
                sale_order.unlink()
                return False

            order_queue_line.write({'state': 'done', 'processed_at': datetime.now(), 'sale_order_id': sale_order.id})
        else:
            message = "Instance not found for site: %s" % ebay_site.name if ebay_site else ''
            _logger.info(message)
            log_line = log_lines_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                                model_name='sale.order', order_ref=order_ref,
                                                                log_line_type='fail', mismatch=True)
            log_line.write({'ebay_order_data_queue_line_id': order_queue_line.id})
            order_queue_line.write({'state': 'failed', 'processed_at': datetime.now()})

        return sale_order

    def ebay_check_mismatch_details_for_order(self, instance, order_response, order_queue_line):
        """
        This method is use to check the mismatch details for payment, workflow and product.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 12 January 2022 .
        Task_id: 180141 - Import Shipped Orders
        """
        skip_order = self.check_payment_details_and_workflow_ept(instance, order_response, order_queue_line)
        if not skip_order:
            skip_order = self.check_product_mismatch_details(instance, order_response, order_queue_line)
            if not skip_order:
                self.get_ebay_shipping_details(instance, order_response, order_queue_line)

        return skip_order

    def check_payment_details_and_workflow_ept(self, instance, order_response, order_queue_line):
        """
        This method is use to check the payment details in order response.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 6 January 2022 .
        Task_id: 180140 - Import Unshipped Orders
        """
        log_lines_obj = self.env['common.log.lines.ept']
        order_ref = order_response['OrderID']
        order_checkout_status = order_response['CheckoutStatus']
        payment_status = order_checkout_status['eBayPaymentStatus']
        payment_method = order_checkout_status['PaymentMethod']
        skip_order = False
        message = ''
        payment_option = self.get_payment_option_and_method(instance, order_response)

        if payment_status in ('BuyerCreditCardFailed', 'BuyerECheckBounced'):
            message = _("Order %s skipped due to Payment Status is: %s", order_ref, payment_status)
        elif not payment_option:
            message = _("Order %s skipped due to auto workflow configuration not found for payment method: %s "
                        "\n You can find workflow configuration here: eBay > Configuration > Payment Options",
                        order_ref, payment_method)
        elif payment_option and not payment_option.payment_term_id:
            message = _("Order %s skipped due to Payment Term not found in payment method: %s", order_ref,
                        payment_method)
        if message:
            skip_order = True
            log_line = log_lines_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                                model_name='sale.order', order_ref=order_ref,
                                                                log_line_type='fail', mismatch=True,
                                                                ebay_instance_id=instance.id)
            log_line.write({'ebay_order_data_queue_line_id': order_queue_line.id})
            order_queue_line.write({'state': 'failed', 'processed_at': datetime.now()})
        return skip_order

    def check_product_mismatch_details(self, instance, order_response, order_queue_line):
        """
        This method is use to check the mismatch details of products for a order.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 6 January 2022 .
        Task_id: 180140 - Import Unshipped Orders
        """
        log_lines_obj = self.env['common.log.lines.ept']
        transaction_array = order_response.get('TransactionArray', False)
        order_lines = transaction_array and transaction_array.get('Transaction', [])
        item_id = False
        for order_line in order_lines:
            ebay_sku = order_line.get('Variation', {}).get('SKU', False)
            if not ebay_sku:
                ebay_sku = order_line.get('Item', {}).get('SKU', False)
                item_id = order_line.get('Item', {}).get('ItemID', {})
            if not any([ebay_sku, item_id]):
                message = _("Order %s skipped due to SKU or Item id not found in order response %s",
                            order_response.get('OrderID'))
                _logger.info(message)
                log_line = log_lines_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                                    model_name='sale.order',
                                                                    ebay_instance_id=instance.id,
                                                                    order_ref=order_response.get('OrderID', False),
                                                                    log_line_type='fail', mismatch=True)
                log_line.write({'ebay_order_data_queue_line_id': order_queue_line.id})
                order_queue_line.write({'state': 'failed', 'processed_at': datetime.now()})
                return True
            return self.search_create_product_for_order_ept(order_response, item_id, ebay_sku, instance,
                                                            order_queue_line)

    def search_create_product_for_order_ept(self, order_response, item_id, ebay_sku, instance, order_queue_line):
        """
        This method is use to search the product in ebay layer and call the sync product listing process.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 7 January 2022.
        Task_id: 180140 - Import Unshipped Orders
        """
        log_lines_obj = self.env['common.log.lines.ept']
        listing_obj = self.env['ebay.product.listing.ept']
        ebay_product_product_obj = self.env["ebay.product.product.ept"]
        listing = listing_obj.search([('name', '=', item_id), ('instance_id', '=', instance.id)],
                                     order='id desc', limit=1)
        if not listing:
            ebay_product = ebay_product_product_obj.search(
                [('ebay_sku', '=', ebay_sku), ('instance_id', '=', instance.id)], limit=1)
            if not ebay_product and not instance.seller_id.create_new_product:
                message = _("Order %s skipped due to SKU(%s) or Item(%s) id not found in Odoo" % (
                    order_response.get('OrderID'), ebay_sku, item_id))
                log_line = log_lines_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                                    model_name='sale.order',
                                                                    ebay_instance_id=instance.id,
                                                                    order_ref=order_response.get('OrderID', False),
                                                                    log_line_type='fail', mismatch=True)
                log_line.write({'ebay_order_data_queue_line_id': order_queue_line.id})
                order_queue_line.write({'state': 'failed', 'processed_at': datetime.now()})
                return True
            if not ebay_product and instance.seller_id.create_new_product:
                try:
                    item_response = ebay_product_product_obj.call_get_items_ebay_api(instance, item_id)
                except Exception as error:
                    log_line = log_lines_obj.create_common_log_line_ept(message=str(error), module='ebay_ept',
                                                                        model_name='sale.order',
                                                                        ebay_instance_id=instance.id,
                                                                        order_ref=order_response.get('OrderID', False),
                                                                        log_line_type='fail', mismatch=False)
                    log_line.write({'ebay_order_data_queue_line_id': order_queue_line.id})
                    order_queue_line.write({'state': 'failed', 'processed_at': datetime.now()})
                    return True
                item_response = item_response.get('Item')
                _logger.info("Start Processing ItemId: %s and name: %s" % (
                    (item_response['ItemID']), item_response.get('Title')))
                product_data_queue_obj = self.env["ebay.import.product.queue"]
                seller_id = instance.seller_id
                product_queue, last_product_queue = product_data_queue_obj.create_product_queue(seller_id,
                                                                                                [item_response], False,
                                                                                                is_create_odoo_product=seller_id.create_new_product,
                                                                                                is_sync_stock=seller_id.ebay_is_sync_stock,
                                                                                                is_sync_price=seller_id.ebay_is_sync_price)
                listing_obj.create_or_update_product_with_listings(instance, item_response,
                                                                   last_product_queue.import_product_queue_line_ids)
                _logger.info("End Processing ItemId: %s and name: %s" % ((item_response['ItemID']), item_response.get(
                    'Title')))
                last_product_queue.import_product_queue_line_ids.write(
                    {'processed_at': datetime.now(), 'state': 'done'})
        return False

    def create_ebay_sale_order_lines(self, order_response, instance, sale_order, order_queue):
        """
        Create shipping order line and order discount line and sale order line.
        :param order_response: order dictionary received from eBay API
        :param instance: instance of eBay
        :param ebay_order: sale order object
        """
        sale_order_line_obj = self.env['sale.order.line']
        sale_order_lines = sale_order_line_obj.create_ebay_sale_order_line(order_response, instance, sale_order,
                                                                           order_queue)
        if not sale_order_lines:
            return False
        order_discounts = order_response.get('SellerDiscounts', {}).get('SellerDiscount')
        if order_discounts is None:
            order_discounts = []
        if isinstance(order_discounts, dict):
            order_discounts = [order_discounts]
        for order_discount in order_discounts:
            seller_dis_val = float(order_discount.get('ItemDiscountAmount').get('value', 0.0))
            ship_dis_val = float(order_discount.get('ShippingDiscountAmount').get('value', 0.0))
            if seller_dis_val > 0.0:
                sale_order_line_obj.create_discount_product_order_line(sale_order, instance, seller_dis_val,
                                                                       order_discount)
            if ship_dis_val > 0.0:
                sale_order_line_obj.create_discount_product_order_line(sale_order, instance, ship_dis_val,
                                                                       order_discount)
        return sale_order_lines

    def create_ebay_sales_order_values(self, partner, shipping_partner, order_response, instance):
        """
        Prepare dictionary for eBay sale order
        :param partner: partner and invoice partner
        :param shipping_partner: shipping partner
        :param order_dict: order dictionary received from eBay API
        :param instance: instance of eBay
        :return: Dictionary of sale order values
        Migration done by Haresh Mori @ Emipro on date 8 January 2022 .
        """
        delivery_carrier = self.search_ebay_delivery_carrier(order_response)
        payment_option = self.get_payment_option_and_method(instance, order_response)
        order_values = self.create_order_values_dict(instance, order_response, partner, shipping_partner,
                                                     payment_option, delivery_carrier)
        # order_values = self.create_sales_order_vals_ept(order_values)
        ebay_site = self.get_ebay_order_site(order_response)
        order_values.update({
            'ebay_instance_id': instance and instance.id or False,
            'ebay_seller_id': instance and instance.seller_id.id or False,
            'ebay_buyer_id': order_response.get('BuyerUserID', ''),
            'ebay_order_id': order_response.get('OrderID', False),
            'auto_workflow_process_id': payment_option and payment_option.auto_workflow_id.id or False,
            'ebay_payment_option_id': payment_option and payment_option.id or False,
            'ebay_site_id': ebay_site.id if ebay_site else False,
            'selling_manager_sales_record_number': order_response.get('ShippingDetails', {}).get(
                'SellingManagerSalesRecordNumber', '')
        })
        if not instance.seller_id.ebay_is_use_default_sequence:
            name = "%s%s" % (instance.seller_id.order_prefix or '', order_response.get('OrderID'))
            order_values.update({"name": name})
        return order_values

    @staticmethod
    def create_order_values_dict(instance, order_dict, partner, shipping_partner, payment_option, delivery_carrier):
        """
        Create dictionary for order values
        :param instance: eBay instance object.
        :param order_dict: Order dictionary received from eBay.
        :param partner: partner object
        :param shipping_partner: delivery type partner
        :param payment_option: payment option
        :param delivery_carrier: Delivery carrier object
        :return: dictionary of order values
        """
        order_values = {
            'company_id': instance.seller_id.company_id.id,
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': shipping_partner.id,
            'warehouse_id': instance.warehouse_id.id,
            'picking_policy': payment_option.auto_workflow_id.picking_policy or False,
            'date_order': instance.odoo_format_date(order_dict.get('CreatedTime', False)),
            'pricelist_id': instance.pricelist_id.id or False,
            'payment_term_id': payment_option.payment_term_id.id or False,
            'team_id': instance.seller_id.ebay_team_id and instance.seller_id.ebay_team_id.id or False,
            'carrier_id': delivery_carrier and delivery_carrier.id or False,
            'client_order_ref': order_dict.get('BuyerUserID', '')
        }
        return order_values

    def get_ebay_shipping_details(self, instance, order_response, order_queue_line):
        """
        Find or create Delivery Carrier as per carrier code in shipment report
        :param order_response: Order response received from eBay.
        :param instance: eBay instance object
        :param order_queue_line: order data queue line id
        :return carrier.id: delivery carrier id
        """
        delivery_carrier = self.search_ebay_delivery_carrier(order_response)
        shipping_service_name = order_response.get('ShippingServiceSelected', {}).get('ShippingService', False)
        seller_id = instance.seller_id
        if not delivery_carrier and instance.seller_id.ebay_is_create_delivery_carrier:
            ship_product_id = seller_id.shipment_charge_product_id.id
            self.env['delivery.carrier'].create(
                {'name': shipping_service_name, 'product_id': ship_product_id, 'ebay_code': shipping_service_name})
        return False

    def search_ebay_delivery_carrier(self, order_dict):
        """
        Search delivery carrier based on eBay code and shipping service.
        :param order_dict: Order response received from eBay.
        :return: delivery carrier object and Shipping service name
        Migration done by Haresh Mori @ Emipro on date 8 January 2022 .
        """
        delivery_carrier_obj = self.env['delivery.carrier']
        shipping_service_name = order_dict.get('ShippingServiceSelected', {}).get('ShippingService', False)
        delivery_carrier = delivery_carrier_obj.search(
            ['|', ('ebay_code', '=', shipping_service_name), ('name', '=', shipping_service_name)], limit=1)
        return delivery_carrier

    def ebay_process_auto_invoice_workflow(self, sale_order, instance, order_response, order_queue_line, order_queue):
        """
        This method is use to process the auto invoice workflow in order
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 12 January 2022 .
        Task_id: 180141 - Import Shipped Orders
        """
        log_lines_obj = self.env['common.log.lines.ept']
        payment_option = self.get_payment_option_and_method(instance, order_response)
        try:
            if order_queue.queue_type == 'shipped':
                _logger.info("Processing shipped workflow")
                payment_option.auto_workflow_id.shipped_order_workflow_ept(sale_order)
            else:
                _logger.info("Processing workflow ")
                sale_order.process_orders_and_invoices_ept()
        except Exception as error:
            message = "Receive error while process auto invoice workflow, Error is:  (%s)" % (error)
            _logger.info(message)
            log_line = log_lines_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                                model_name='sale.order', order_ref=sale_order.name,
                                                                log_line_type='fail', mismatch=False,
                                                                ebay_instance_id=instance.id)
            log_line.write({'ebay_order_data_queue_line_id': order_queue_line.id})
            order_queue_line.write({'state': 'failed', 'processed_at': datetime.now()})

        return True

    def ebay_update_order_status(self, instance):
        """
        This method is use to update Order Status from Odoo to eBay using CompleteSale API.
        Migration done by Haresh Mori @ Emipro on date 17 January 2022 .
        """
        log_lines_obj = self.env['common.log.lines.ept']
        trading_api = instance.get_trading_api_object()
        pickings = self.ebay_search_picking_for_update_order_status(instance)
        updated_ebay_orders = self.check_update_order_status_on_ebay_store_ept(instance, pickings)
        for picking in pickings:
            carrier_name = self.get_ebay_carrier(picking)
            sale_order = picking.sale_id
            _logger.info("We are processing Sale order '%s' and Picking '%s' for update order status", sale_order.name,
                         picking.name)
            if sale_order.ebay_order_id in updated_ebay_orders:
                _logger.info(
                    "Already updated status on ebay for Sale order '%s' and Picking '%s' for update order status",
                    sale_order.name, picking.name)
                picking.write({'updated_in_ebay': True})
                continue
            order_lines = sale_order.order_line.filtered(lambda ol: ol.product_id.detailed_type != 'service' and
                                                                    not ol.display_type)
            if order_lines and order_lines.filtered(lambda s: not s.ebay_order_line_item_id):
                message = (_(
                    "- Order status could not be updated for order %s.\n- Possible reason can be, ebay order line "
                    "reference is missing, which is used to update ebay order status at eBay store. "
                    "\n- This might have happen because user may have done changes in order "
                    "manually, after the order was imported.", sale_order.name))
                _logger.info(message)
                log_lines_obj.create_common_log_line_ept(message=message, module='ebay_ept',
                                                         model_name='sale.order', order_ref=sale_order.name,
                                                         log_line_type='fail', mismatch=True,
                                                         ebay_instance_id=instance.id)
                continue
            for order_line in order_lines.filtered(
                    lambda s: s.product_id.detailed_type != 'service' and s.ebay_order_line_item_id):
                tracking_dict = self.ebay_prepare_tracking_info(picking, carrier_name, order_line)
                update_order_parameter = self.prepare_ebay_update_order_parameter_dict(order_line, sale_order,
                                                                                       tracking_dict)
                try:
                    _logger.info("Prepare data for update shipment: %s", update_order_parameter)
                    trading_api.execute('CompleteSale', update_order_parameter)
                    results = trading_api.response.dict()
                    ack = results and results.get('Ack', False)
                    if ack != 'Failure':
                        picking.write({'updated_in_ebay': True})
                except Exception as error:
                    _logger.info("Failed to update orders status from odoo to eBay : {}".format(error))
                    log_lines_obj.create_common_log_line_ept(message=str(error), module='ebay_ept',
                                                             model_name='sale.order', order_ref=sale_order.name,
                                                             log_line_type='fail', mismatch=False,
                                                             ebay_instance_id=instance.id)
        instance.seller_id.write({'last_update_order_export_date': datetime.now()})

    def check_update_order_status_on_ebay_store_ept(self, instance, pickings):
        """
        This method is used to check whether the order status is updated on ebay store or not.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 11 April 2023 .
        Task_id: 224048 - Update orders status changes
        """

        updated_ebay_orders = []
        trading_api = instance.get_trading_api_object()
        for ebay_order_ids in split_every(20, pickings.sale_id.mapped('ebay_order_id')):
            try:
                trade_api_param = {'OrderIDArray': {'OrderID': list(ebay_order_ids)}, 'DetailLevel': 'ReturnAll'}
                trading_api.execute('GetOrders', trade_api_param)
                results = trading_api.response.dict()
                orders = []
                if results.get('OrderArray', {}) and results['OrderArray'].get('Order', []):
                    orders = results['OrderArray'].get('Order', [])
            except Exception as error:
                raise UserError(error)
            if isinstance(orders, dict):
                orders = [orders]
            for result in orders:
                if result.get('ShippedTime'):
                    updated_ebay_orders.append(result.get('OrderID'))
        return updated_ebay_orders

    def ebay_search_picking_for_update_order_status(self, instance):
        """
        This method is used to search picking for the update order status.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 January 2022 .
        Task_id: 180144 - Update Shipment and Payment Status
        """
        location_obj = self.env["stock.location"]
        stock_picking_obj = self.env["stock.picking"]
        customer_locations = location_obj.search([("usage", "=", "customer")])
        picking_ids = stock_picking_obj.search([("ebay_instance_id", "=", instance.id),
                                                ("updated_in_ebay", "=", False),
                                                ("state", "=", "done"),
                                                ("location_dest_id", "in", customer_locations.ids),
                                                ('is_ebay_delivery_order', '=', True)],
                                               order="date")
        return picking_ids

    def get_ebay_carrier(self, picking):
        """
        Gives carrier name from picking, if available.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 January 2022 .
        Task_id:180144 - Update Shipment and Payment Status
        """
        carrier_name = ""
        if picking.carrier_id:
            carrier_name = (picking.carrier_id.ebay_code or picking.carrier_id.name) or False
            if carrier_name:
                carrier_name = carrier_name.replace("_", "-")
        return carrier_name

    def ebay_prepare_tracking_info(self, picking, carrier_name, order_line):
        """
        This method is use to prepare dictionary values for the update order status from odoo to eBay.
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 17 January 2022 .
        Task_id: 180144 - Update Shipment and Payment Status
        """
        tracking_numbers = []
        tracking_shipment = []
        if picking.mapped("package_ids").filtered(lambda l: l.tracking_no):
            moves = picking.move_lines
            product_moves = moves.filtered(
                lambda x: x.sale_line_id.product_id == x.product_id and x.state == "done")
            for move in product_moves:
                if move.product_id.id == order_line.product_id.id and move.sale_line_id.id == order_line.id:
                    for move_line in move.move_line_ids:
                        tracking_no = move_line.result_package_id.tracking_no or ""
                        tracking_numbers.append(tracking_no)

            kit_move_lines = moves.filtered(
                lambda x: x.sale_line_id.product_id != x.product_id and x.state == "done")
            existing_sale_line_ids = []
            for move in kit_move_lines:
                if move.product_id.id == order_line.product_id.id and move.sale_line_id.id == order_line.id:
                    if move.sale_line_id.id in existing_sale_line_ids:
                        continue
                    existing_sale_line_ids.append(move.sale_line_id.id)

                    tracking_no = move.move_line_ids.result_package_id.mapped("tracking_no") or []
                    tracking_no = tracking_no[0] if tracking_no else ""
                    tracking_numbers.append(tracking_no)
        else:
            if picking.carrier_tracking_ref:
                tracking_numbers.append(picking.carrier_tracking_ref)

        for tracking_ref in list(set(tracking_numbers)):
            tracking_shipment.append({'ShipmentTrackingNumber': tracking_ref, 'ShippingCarrierUsed': carrier_name})
        return tracking_shipment

    def prepare_ebay_update_order_parameter_dict(self, order_line, ebay_order, tracking_shipment):
        """
        Prepare dictionary for update order status parameter.
        :param order_line: eBay sale order line.
        :param ebay_order: sale order object.
        :param instance: eBay instance object.
        :param tracking_shipment: dictionary of tracking shipment.
        :return: Dictionary of update order status parameters.
        """
        ebay_order_line_item_id = order_line.ebay_order_line_item_id
        transaction_split = ebay_order_line_item_id.split("-")
        item_id = transaction_split[0]
        update_order_parameter = {
            'ItemID': item_id,
            'TransactionID': transaction_split[1],
            'OrderID': ebay_order.ebay_order_id,
            'OrderLineItemID': ebay_order_line_item_id
        }
        if tracking_shipment:
            shipment = {'Shipped': True, 'Shipment': {'ShipmentTrackingDetails': tracking_shipment}}
        else:
            shipment = {'Shipped': True}
        update_order_parameter.update(shipment)
        return update_order_parameter

    def check_order_is_ebay_remit_tax(self, order_response):
        """
        This method is check order total and payment amount. if both are not same then it will true the
        'is_ebay_tax_remit' boolean ,by default is false.
        Added MultiLegShippingDetails related condition. when in order MultiLegShippingDetails then take shipping
        cost from the MultiLegShippingDetails tag -> TotalShippingCost.
        Migration done by Haresh Mori @ Emipro on date 8 January 2022 .
        """
        is_ebay_remit_tax = False
        transaction_array = order_response.get('TransactionArray', False)
        order_lines = transaction_array and order_response['TransactionArray'].get('Transaction', [])

        payment_details = order_response.get('MonetaryDetails', {}).get('Payments', {}).get('Payment', {})

        if isinstance(payment_details, dict):
            payment_details = [payment_details]
        payment_amount = 0.0
        for payment_detail in payment_details:
            if payment_detail.get('Payee', {}).get('_type') == 'eBayUser':
                payment_amount += float(payment_detail.get('PaymentAmount', {}).get('value', 0.0))

        if isinstance(order_lines, dict):
            order_lines = [order_lines]
        total_transaction_price = 0.0
        for order_line_dict in order_lines:
            transaction_price = order_line_dict.get('TransactionPrice', False)
            item_price = transaction_price and order_line_dict['TransactionPrice'].get('value', 0.0)
            total_transaction_price += float(item_price)

            shipping_costs = float(order_line_dict.get('ActualShippingCost', {}).get('value', 0.0))
            if order_response.get('IsMultiLegShipping').lower() == 'true' and order_response.get(
                    'MultiLegShippingDetails'):
                shipping_costs = float(
                    order_response.get('MultiLegShippingDetails', {}).get('SellerShipmentToLogisticsProvider', {}).get(
                        'ShippingServiceDetails', {}).get('TotalShippingCost', {}).get('value', 0.0))

            if shipping_costs >= 0.0:
                total_transaction_price += shipping_costs

            total_taxes = float(order_line_dict.get('Taxes', {}).get('TotalTaxAmount', {}).get('value', 0.0))
            if total_taxes:
                total_transaction_price += total_taxes

        total_transaction_price = round(total_transaction_price, 2)
        payment_amount = round(float(payment_amount), 2)
        if total_transaction_price != payment_amount:
            is_ebay_remit_tax = True
        return is_ebay_remit_tax
