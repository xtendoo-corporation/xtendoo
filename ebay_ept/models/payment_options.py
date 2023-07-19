#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describe & get eBay payment options.
"""
from odoo import models, fields, api


class EbayPaymentOptions(models.Model):
    """
    Describes eBay Payment Options
    """
    _name = "ebay.payment.options"
    _description = "eBay Payment Options"
    _order = 'id desc'
    seller_id = fields.Many2one("ebay.seller.ept", string="Seller", required=True, help="eBay Seller")
    name = fields.Char("PaymentOption", required=True, help="Name of Payment Option")
    detail_version = fields.Char("Details Version", help="Payment Option Detail Version")
    description = fields.Char("Payment Description", required=True, help="Payment Description")
    auto_workflow_id = fields.Many2one("sale.workflow.process.ept", "Auto Workflow", help="Set Auto workflow")
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', help="Set Payment Term")
    update_payment_in_ebay = fields.Boolean("Update Payment in eBay", default=False,
                                            help="Checked if payment updated in eBay")

    @api.model
    def get_payment_options(self, seller, options):
        """
        Create/ Update Payment Options received from eBay.
        :param seller: seller of eBay
        :param options: Options received from eBay
        """
        for option in options:
            payment_option = self.search([('seller_id', '=', seller.id), ('name', '=', option.get('PaymentOption'))])
            if payment_option:
                payment_option.write({'detail_version': option.get('DetailVersion'),
                                      'description': option.get('Description')})
            else:
                self.create({'seller_id': seller.id, 'name': option.get('PaymentOption'),
                             'detail_version': option.get('DetailVersion'), 'description': option.get('Description'),
                             'auto_workflow_id': self.env.ref('common_connector_library.automatic_validation_ept',
                                                              raise_if_not_found=False).id,
                             'payment_term_id': self.env.ref('account.account_payment_term_immediate',
                                                             raise_if_not_found=False).id
                             })
        return True
