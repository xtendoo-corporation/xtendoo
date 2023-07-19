#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods for account move
"""
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """
    Account Invoice for ebay
    """
    _inherit = 'account.move'

    ebay_instance_id = fields.Many2one("ebay.instance.ept", string="eBay Site")
    ebay_seller_id = fields.Many2one("ebay.seller.ept", string="eBay Seller")
    ebay_payment_option_id = fields.Many2one('ebay.payment.options', string="Payment Option")
    payment_updated_in_ebay = fields.Boolean(
        string="Payment Updated In eBay ?", compute='_compute_get_ebay_updated_status', store=True, default=False)
    payment_partially_updated_in_ebay = fields.Boolean(
        string="Payment Partially Updated In eBay ?", compute='_compute_get_ebay_updated_status', compute_sudo=True)
    is_refund_in_ebay = fields.Boolean(string="Is refund in eBay ?", default=False)
    visible_payment_option = fields.Boolean(
        string="Visible Invoice Payment Option", compute="_compute_get_payment_option", store=True)
    # 'visible_update_payment_in_ebay' Added by Tushal Nimavat on 29/06/2022
    visible_update_payment_in_ebay = fields.Boolean(string="Visible Update Payment In eBay",
                                                    compute="_compute_get_update_payment_in_ebay", store=True)

    @api.depends('ebay_payment_option_id')
    def _compute_get_update_payment_in_ebay(self):
        """
        Get option for Update Payment In eBay
        Added by Tushal Nimavat on 30/06/2022
        """
        for invoice in self:
            if invoice.state == 'posted' and invoice.ebay_instance_id \
                    and invoice.ebay_payment_option_id.update_payment_in_ebay and invoice.move_type == 'out_invoice' \
                    and not invoice.payment_updated_in_ebay:
                invoice.visible_update_payment_in_ebay = True
            else:
                invoice.visible_update_payment_in_ebay = False

    @api.model
    def default_get(self, fields_list):
        res = super(AccountMove, self).default_get(fields_list)
        if 'payment_partially_updated_in_ebay' in res.keys() and res['payment_partially_updated_in_ebay'] is None:
            res['payment_partially_updated_in_ebay'] = False
            res['payment_updated_in_ebay'] = False
            res['is_refund_in_ebay'] = False
        return res

    @api.depends("invoice_line_ids.payment_updated_in_ebay")
    def _compute_get_ebay_updated_status(self):
        """
        This method is use to set the payment updated status in invoice and invoice line.
        Migration done by Haresh Mori @ Emipro on date 17 January 2022 .
        """
        for invoice in self:
            if invoice.ebay_instance_id:
                payment_partially_updated_in_ebay = invoice.payment_partially_updated_in_ebay
                inv_ln_ids = invoice.invoice_line_ids
                inv_payment_state = invoice.payment_state
                inv_cond = (inv_payment_state == 'paid' and inv_ln.payment_updated_in_ebay for inv_ln in inv_ln_ids)
                if not payment_partially_updated_in_ebay:
                    payment_partially_updated_in_ebay = any(inv_cond)
                if payment_partially_updated_in_ebay:
                    payment_partially_updated_in_ebay = not all(inv_cond)
                    invoice.payment_updated_in_ebay = not payment_partially_updated_in_ebay
                else:
                    invoice.payment_updated_in_ebay = False
            else:
                invoice.payment_updated_in_ebay = False
                invoice.payment_partially_updated_in_ebay = False

    @api.depends('ebay_payment_option_id', 'invoice_line_ids')
    def _compute_get_payment_option(self):
        """
        Get payment options for ebay orders invoices
        Migration done by Haresh Mori @ Emipro on date 17 January 2022 .
        """
        for invoice in self:
            sales = invoice.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
            sale = sales and sales[0]
            ebay_payment_option_id = invoice.ebay_payment_option_id
            if not sale or invoice.move_type != 'out_invoice' or not invoice.ebay_payment_option_id or \
                ebay_payment_option_id.name == 'PayPal':
                invoice.visible_payment_option = False
                continue
            if ebay_payment_option_id and not ebay_payment_option_id.update_payment_in_ebay:
                invoice.visible_payment_option = False
                continue
            invoice.visible_payment_option = True

    def action_invoice_paid(self):
        """
        Returns paid invoices of eBay
        """
        result = super(AccountMove, self).action_invoice_paid()
        for invoice in self:
            instance = invoice.ebay_instance_id
            ebay_payment_option_id = invoice.ebay_payment_option_id
            if instance and instance.seller_id.auto_update_payment and invoice.move_type == 'out_invoice' and ebay_payment_option_id:
                if ebay_payment_option_id.name == 'PayPal' or invoice.payment_updated_in_ebay or not \
                    ebay_payment_option_id.update_payment_in_ebay:
                    return result
                invoice.update_payment_in_ebay()
        return result

    def call_payment_update_api(self, instance, invoice_lines, para):
        """
        Call Payment update from ebay API
        :param instance: instance of ebay
        :param invoice_lines: invoice lines object
        :param para: parameters to be send to ebay API
        """
        try:
            lang = instance.lang_id and instance.lang_id.code
            if lang:
                para.update({'ErrorLanguage': lang})
            trade_api = instance.get_trading_api_object()
            trade_api.execute('ReviseCheckoutStatus', para)
            trade_api.response.dict()
            invoice_lines.write({'payment_updated_in_ebay': True})
            self._cr.commit()
        except Exception as error:
            raise UserError(error)

    def update_payment_in_ebay(self):
        """
        This method is use to update invoice payment in eBay store via API.
        Migration done by Haresh Mori @ Emipro on date 17 January 2022 .
        """
        self.ensure_one()
        sales = self.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
        sale = sales and sales[0]
        instance = self.ebay_instance_id if self.ebay_instance_id.active else False
        if instance and sale or (self.ebay_payment_option_id and self.ebay_payment_option_id.update_payment_in_ebay and
                                 self.ebay_payment_option_id.name != 'PayPal'):
            _logger.info("Processing update payment for invoice: %s", self.name)
            flag = True
            shipping_charge = 0.0
            discount = 0.0
            invoice_line_ids = []
            for invoice_line in self.invoice_line_ids.filtered(
                lambda line: line.product_id and not line.payment_updated_in_ebay):
                order_line = invoice_line.sale_line_ids[0]
                item_id = order_line.item_id
                inv_product_id = invoice_line.product_id
                inv_quantity = invoice_line.quantity
                if order_line and item_id and inv_product_id.detailed_type == 'product':
                    if flag:
                        invoice_line_ids.append(invoice_line.id)
                        flag = False
                        remaining_payment_update_parameters = self.prepare_update_payment_parameters_dict(inv_quantity,
                                                                                                          invoice_line,
                                                                                                          item_id,
                                                                                                          order_line,
                                                                                                          sale.ebay_order_id)
                    else:
                        payment_update_parameters = self.prepare_update_payment_parameters_dict(inv_quantity,
                                                                                                invoice_line, item_id,
                                                                                                order_line,
                                                                                                sale.ebay_order_id)
                        _logger.info("Prepare data for update payment: %s", payment_update_parameters)
                        self.call_payment_update_api(instance, invoice_line, payment_update_parameters)

                elif order_line and item_id and inv_product_id.detailed_type == 'service':
                    invoice_line_ids.append(invoice_line.id)
                    if invoice_line.price_subtotal > 0.0:
                        shipping_charge = shipping_charge + (inv_quantity * invoice_line.price_unit)
                    else:
                        discount = discount + (inv_quantity * invoice_line.price_unit)
            if not flag:
                if discount != 0.0:
                    remaining_payment_update_parameters.update({'AdjustmentAmount': discount})
                if shipping_charge != 0.0:
                    remaining_payment_update_parameters.update({'ShippingCost': shipping_charge})
                invoice_lines = self.env['account.move.line'].browse(invoice_line_ids)
                _logger.info("Prepare data for update payment: %s", remaining_payment_update_parameters)
                self.call_payment_update_api(instance, invoice_lines, remaining_payment_update_parameters)

    def prepare_update_payment_parameters_dict(self, inv_quantity, invoice_line, item_id, order_line, ebay_order_id):
        """
        Prepare dictionary for update payments parameters.
        :param inv_quantity: invoice quantity
        :param invoice_line: invoice line object
        :param item_id: eBay item id
        :param order_line: sale order line object
        :param ebay_order_id: eBay order id
        :return: dictionary of update payment parameters.
        Migration done by Haresh Mori @ Emipro on date 17 January 2022 .
        """
        return {
            'AmountPaid': inv_quantity * invoice_line.price_unit,
            'ItemID': item_id,
            'CheckoutStatus': 'Complete',
            'OrderLineItemID': order_line.ebay_order_line_item_id,
            'PaymentMethodUsed': self.ebay_payment_option_id.name,
            'OrderID': ebay_order_id,
        }

    @api.model
    def _prepare_refund(
        self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        """
        Prepare refund of specific invoice
        :param invoice: account invoice object
        :param date_invoice: date of invoice
        :param date: current date
        :param description: description for refund
        :param journal_id:  account journal object
        :return: dictionary for prepare refund
        """
        values = super(AccountMove, self)._prepare_refund(
            invoice, date_invoice=date_invoice, date=date, description=description, journal_id=journal_id)
        if invoice.ebay_instance_id:
            values.update({'ebay_instance_id': invoice.ebay_instance_id.id})
        return values
