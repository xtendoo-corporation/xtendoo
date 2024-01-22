# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################

from odoo import api, fields, models, _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def get_coupon_settings(self):
        IrDefault = self.env['ir.default'].sudo()
        config_obj = dict(
            voucher_creation_product=IrDefault.get(
                'res.config.settings', 'voucher_creation_product'),
            refund_coupon_partial_redeem=IrDefault.get(
                'res.config.settings', 'refund_coupon_partial_redeem') or False,
            refund_coupon_validity=IrDefault.get(
                'res.config.settings', 'refund_coupon_validity'),
        )
        return config_obj

    def get_coupon_values(self, amount, partner_id, name):
        config_obj = self.get_coupon_settings()
        vals = dict(
            voucher_value=amount,
            validity=config_obj.get('refund_coupon_validity'),
            expiry_date=str(datetime.today().date(
            )+relativedelta(days=config_obj.get('refund_coupon_validity'))),
            voucher_val_type='amount',
            use_minumum_cart_value=False,
            is_partially_redemed=config_obj.get(
                'refund_coupon_partial_redeem'),
            voucher_usage='both',
            total_available=config_obj.get('default_availability') or 1,
            issue_date=str(datetime.today().date()),
            available_each_user=1,
            customer_type=partner_id and 'special_customer' or 'general',
            customer_id=partner_id or False,
            applied_on='all',
            name=name)
        return vals

    @api.model
    def create_from_ui(self, orders, draft):
        order_ids = return_data = super(
            PosOrder, self).create_from_ui(orders, draft)
        result = {}
        if type(return_data) == dict:
            result = return_data
        else:
            result['order_ids'] = order_ids
        result['voucher_ids'] = []
        for order in orders:
            order_obj = self.search(
                [('pos_reference', '=', order.get('data').get('name'))])
            coupon_name = "Refund Voucher (%s)" % order_obj.name
            if order.get('data').get('to_voucher_refund') and order.get('data').get('refund_voucher_amount') > 0:
                vals = self.get_coupon_values(amount=order.get('data').get(
                    'refund_voucher_amount'), partner_id=order.get('data').get('partner_id', False), name=coupon_name)
                try:
                    voucher_id = self.env['voucher.voucher'].create(vals)
                    voucher_history_obj = self.env['voucher.history'].sudo().search(
                        [('voucher_id', '=', voucher_id.id), ('transaction_type', '=', 'credit')], limit=1)
                    if voucher_history_obj:
                        voucher_history_obj.pos_order_id = order_obj.id
                        voucher_history_obj.description = "Voucher Created at %s" % str(
                            datetime.today())
                    result['voucher_ids'].append(voucher_id.id)
                except Exception as e:
                    _logger.info(
                        '-------Exception in Creating Gift Card Voucher------%r', e)
        return result


class VoucherVoucher(models.Model):
    _inherit = "voucher.voucher"

    def _validate_n_get_value(self, secret_code, wk_order_total, product_ids, refrence=False, partner_id=False):
        self_obj = self._get_voucher_obj_by_code(secret_code, refrence)
        result = {}
        used_vouchers = 0
        used_vouchers = self.env['voucher.history'].sudo().search(
            [('voucher_id', '=', self_obj.id), ('transaction_type', '=', 'debit')])
        if self_obj.customer_type == 'special_customer':
            if (self_obj.is_partially_redemed != True):
                if len(used_vouchers) >= 1:
                    result['type'] = _('ERROR')
                    result['message'] = _(
                        'Total Availability of this Voucher is 0. You can`t redeem this voucher anymore !!!')
                    return result
        return super(VoucherVoucher, self)._validate_n_get_value(secret_code, wk_order_total, product_ids, refrence, partner_id)
