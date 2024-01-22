# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    voucher_creation_product = fields.Many2one(comodel_name='product.product', string='Refund Product')
    refund_coupon_partial_redeem = fields.Boolean(string='Partially Use Refund Coupon')
    refund_coupon_validity = fields.Integer(string='Refund Coupon Validity(in days)',default=365, help="Validity of this Voucher in days")

    @api.constrains('refund_coupon_validity')
    def check_values(self):
        for data in self:
            if data.refund_coupon_validity <= 0:
                raise ValidationError('Refund Coupon Validity Cannot be set less than or equal to 0')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('res.config.settings', 'voucher_creation_product',self.voucher_creation_product.id)
        IrDefault.set('res.config.settings', 'refund_coupon_partial_redeem',self.refund_coupon_partial_redeem)
        IrDefault.set('res.config.settings', 'refund_coupon_validity',self.refund_coupon_validity)
        return True

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrDefault = self.env['ir.default'].sudo()
        res.update(
            {
                'voucher_creation_product':IrDefault.get('res.config.settings', 'voucher_creation_product'),
                'refund_coupon_partial_redeem':IrDefault.get('res.config.settings', 'refund_coupon_partial_redeem') or False,
                'refund_coupon_validity':IrDefault.get('res.config.settings', 'refund_coupon_validity' ),
            }
        )
        return res