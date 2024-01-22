/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

odoo.define('pos_voucher_refund.popups', function (require) {
    "use strict";
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    // VoucherRefundEditPopup Popup
    class VoucherRefundEditPopup extends AbstractAwaitablePopup {
        shake($element, settings) {
            if (typeof settings.complete == 'undefined') {
                settings.complete = function () { };
            }
            $element.css('position', 'relative');
            for (var iter = 0; iter < (settings.times + 1); iter++) {
                $element.animate({ left: ((iter % 2 == 0 ? settings.distance : settings.distance * -1)) }, settings.interval);
            }
            $element.animate({ left: 0 }, settings.interval, settings.complete);
        }
        update_coupon_amount(event) {
            var self = this;
            var order = this.env.pos.get_order();
            var val = $('.voucher-refund-edit-input').val()
            if (val < self.props.min_amount) {
                self.showPopup('MinAmountPopupWidget', {
                    'default_min_amount': self.props.min_amount,
                    'voucher_amount': self.env.pos.get_order().refund_voucher_amount
                })
            }
            else if (val > self.props.max_amount) {
                self.showPopup('MaxAmountPopupWidget', {
                    'default_max_amount': self.props.max_amount,
                    'voucher_amount': self.env.pos.get_order().refund_voucher_amount
                })
            }
            else if ($.isNumeric(val) && parseFloat(val) > 0) {
                var order = this.env.pos.get_order();
                var lines = order.get_orderlines();
                var voucher_product_id = this.env.pos.db.voucher_configured_product_id;
                lines.forEach(function (line) {
                    if (line.product.id == voucher_product_id) {
                        line.set_unit_price(parseFloat(val));
                        order.refund_voucher_amount = parseFloat(val);
                        order.save_to_db();
                        return true;
                    }
                });
                this.cancel();
            } else {
                $(".voucher-refund-edit-input").css("box-shadow", "inset 0px 0px 0px 1px #ff4545");
                self.shake($(".voucher-refund-edit-input"), {
                    interval: 60,
                    distance: 5,
                    times: 5,
                });
            }
        }
    }
    VoucherRefundEditPopup.template = 'VoucherRefundEditPopup';
    VoucherRefundEditPopup.defaultProps = {
        title: 'Confirm ?',
        value: ''
    };
    Registries.Component.add(VoucherRefundEditPopup);
});
