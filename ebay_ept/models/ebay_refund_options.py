#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes refund options
"""
from odoo import models, fields


class EbayRefundOptions(models.Model):
    """
    Describes Refund Options
    """
    _name = "ebay.refund.options"
    _description = "eBay Refund Options"
    name = fields.Char("Option", required=True)
    description = fields.Char("Refund Description", required=True)
    site_ids = fields.Many2many("ebay.site.details", 'ebay_refund_site_rel', 'refund_id', 'site_id', required=True)

    def create_refund_details(self, instance, details):
        """
        Create if refund details is not available else update refund details.
        :param instance: instance of ebay
        :param details: refund details
        """
        self.create_or_update_refund_options(details.get('Refund', []), instance)
        self.create_or_update_return_days(details.get('ReturnsWithin', []), instance)
        self.create_or_update_shipping_cost_options(details.get('ShippingCostPaidBy', []), instance)
        self.create_or_update_restock_fee_options(details.get('RestockingFeeValue', []), instance)
        return True

    def create_or_update_refund_options(self, refund_details, instance):
        """
        Create or update refund option details.
        :param refund_details: Refund details
        :param instance: eBay instance object
        """
        if not isinstance(refund_details, list):
            refund_details = [refund_details]
        for option in refund_details:
            exist_option = self.search([
                ('name', '=', option.get('RefundOption')), ('site_ids', 'in', instance.site_id.ids)])
            if not exist_option:
                exist_option = self.search([('name', '=', option.get('RefundOption'))])
                if not exist_option:
                    self.create({
                        'name': option.get('RefundOption'), 'description': option.get('Description'),
                        'site_ids': [(6, 0, instance.site_id.ids)]})
                else:
                    site_ids = list(set(exist_option.site_ids.ids + instance.site_id.ids))
                    exist_option.write({'site_ids': [(6, 0, site_ids)]})

    def create_or_update_return_days(self, returns_with_in, instance):
        """
        Create or update return days
        :param returns_with_in: Return days options from eBay
        :param instance: eBay instance object
        """
        return_days_obj = self.env['ebay.return.days']
        if not isinstance(returns_with_in, list):
            returns_with_in = [returns_with_in]
        for option in returns_with_in:
            exist_option = return_days_obj.search([
                ('name', '=', option.get('ReturnsWithinOption')), ('site_ids', 'in', instance.site_id.ids)])
            if not exist_option:
                exist_option = return_days_obj.search([('name', '=', option.get('ReturnsWithinOption'))])
                if not exist_option:
                    return_days_obj.create({
                        'name': option.get('ReturnsWithinOption'), 'description': option.get('Description'),
                        'site_ids': [(6, 0, instance.site_id.ids)]})
                else:
                    site_ids = list(set(exist_option.site_ids.ids + instance.site_id.ids))
                    exist_option.write({'site_ids': [(6, 0, site_ids)]})

    def create_or_update_shipping_cost_options(self, shipping_cost_paid_by, instance):
        """
        Create or update shipping cost options.
        :param shipping_cost_paid_by: Shipping cost paid by received from eBay.
        :param instance: eBay instance object
        """
        shipping_cost_obj = self.env['ebay.refund.shipping.cost.options']
        if not isinstance(shipping_cost_paid_by, list):
            shipping_cost_paid_by = [shipping_cost_paid_by]
        for option in shipping_cost_paid_by:
            exist_option = shipping_cost_obj.search([
                ('name', '=', option.get('ShippingCostPaidByOption')), ('site_ids', 'in', instance.site_id.ids)])
            if not exist_option:
                exist_option = shipping_cost_obj.search([('name', '=', option.get('ShippingCostPaidByOption'))])
                if not exist_option:
                    shipping_cost_obj.create({
                        'name': option.get('ShippingCostPaidByOption'), 'description': option.get('Description'),
                        'site_ids': [(6, 0, instance.site_id.ids)]})
                else:
                    site_ids = list(set(exist_option.site_ids.ids + instance.site_id.ids))
                    exist_option.write({'site_ids': [(6, 0, site_ids)]})

    def create_or_update_restock_fee_options(self, restock_fee_value, instance):
        """
        Create or update restock fee options
        :param restock_fee_value: Restock fee options received from eBay.
        :param instance: eBay instance object.
        """
        restock_fee_obj = self.env['ebay.restock.fee.options']
        if not isinstance(restock_fee_value, list):
            restock_fee_value = [restock_fee_value]
        for option in restock_fee_value:
            exist_option = restock_fee_obj.search([
                ('name', '=', option.get('RestockingFeeValueOption')), ('site_ids', 'in', instance.site_id.ids)])
            if not exist_option:
                exist_option = restock_fee_obj.search([('name', '=', option.get('RestockingFeeValueOption'))])
                if not exist_option:
                    restock_fee_obj.create({
                        'name': option.get('RestockingFeeValueOption'), 'description': option.get('Description'),
                        'site_ids': [(6, 0, instance.site_id.ids)]})
                else:
                    site_ids = list(set(exist_option.site_ids.ids + instance.site_id.ids))
                    exist_option.write({'site_ids': [(6, 0, site_ids)]})
