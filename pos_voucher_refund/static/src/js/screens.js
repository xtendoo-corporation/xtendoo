/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

odoo.define("pos_voucher_refund.screens", function (require) {
    "use strict";
    const Registries = require('point_of_sale.Registries');
    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    var rpc = require('web.rpc');

    // MinAmountPopupWidget Popup
    class MinAmountPopupWidget extends AbstractAwaitablePopup {
    }
    MinAmountPopupWidget.template = 'MinAmountPopupWidget';
    MinAmountPopupWidget.defaultProps = {
        title: 'Confirm ?',
        value: ''
    };
    Registries.Component.add(MinAmountPopupWidget);

    // MaxAmountPopupWidget Popup
    class MaxAmountPopupWidget extends AbstractAwaitablePopup {
    }
    MaxAmountPopupWidget.template = 'MaxAmountPopupWidget';
    MaxAmountPopupWidget.defaultProps = {
        title: 'Confirm ?',
        value: ''
    };
    Registries.Component.add(MaxAmountPopupWidget);

    // Inherit PaymentScreen----------------
    const PosResPaymentScreen = (PaymentScreen) => class extends PaymentScreen {
        setup() {
            super.setup();
            var self = this;
            rpc.query({
                model: 'voucher.voucher',
                method: 'get_default_values',
            }).then(function (result) {
                self.props.wk_coupon_product_id = result.product_id;
                self.props.max_expiry_date = result.max_expiry_date;
                self.props.min_amount = result.min_amount;
                self.props.max_amount = result.max_amount;
            });

            setTimeout(function () {
                var order = self.env.pos.get_order();
                if (order) {
                    if (order.is_return_order || order.get_total_with_tax() < 0)
                        $(".voucher-refund").show();
                    else
                        $(".voucher-refund").hide();
                } else
                    $(".voucher-refund").hide();
                if (order.is_to_voucher_refund()) {
                    $(".voucher-refund").show().addClass('highlight');
                    self.add_voucher_creation_product();
                }
            }, 100);
        }
        async validateOrder(isForceValidate) {
            var self = this;
            if (self.env.pos.get_order().is_to_voucher_refund()) {
                if (self.env.pos.get_order().refund_voucher_amount < self.props.min_amount) {
                    self.showPopup('MinAmountPopupWidget', {
                        'default_min_amount': self.props.min_amount,
                        'voucher_amount': self.env.pos.get_order().refund_voucher_amount
                    })
                }
                else if (self.env.pos.get_order().refund_voucher_amount > self.props.max_amount) {
                    self.showPopup('MaxAmountPopupWidget', {
                        'default_max_amount': self.props.max_amount,
                        'voucher_amount': self.env.pos.get_order().refund_voucher_amount
                    })
                }
                else {
                    super.validateOrder(isForceValidate)
                }
            }
            else {
                super.validateOrder(isForceValidate)
            }
        }
        add_voucher_creation_product() {
            var order = this.env.pos.get_order();
            var amount = order.get_total_with_tax();
            var product = this.env.pos.db.get_product_by_id(this.env.pos.db.voucher_configured_product_id);
            if (amount < 0) {
                order.refund_voucher_amount = amount * -1;
                order.add_product(product, {
                    price: amount * -1,
                });
            }
        }
        remove_voucher_creation_product() {
            var order = this.env.pos.get_order();
            var lines = order.get_orderlines();
            var voucher_product_id = this.env.pos.db.voucher_configured_product_id;
            lines.forEach(function (line) {
                if (line.product.id == voucher_product_id) {
                    order.remove_orderline(line);
                    order.refund_voucher_amount = 0.0;
                }
            });
        }
        click_voucher_refund(event) {
            var self = this;
            var order = this.env.pos.get_order();
            order.set_to_voucher_refund(!order.is_to_voucher_refund());
            if (order.is_to_voucher_refund()) {
                $('.voucher-refund').addClass('highlight');
                self.add_voucher_creation_product();
            } else {
                $('.voucher-refund').removeClass('highlight');
                self.remove_voucher_creation_product();
            }
            this.render();
            order.save_to_db();
        }
        click_voucher_refund_edit(event) {
            var order = this.env.pos.get_order();
            event.stopPropagation();
            var min_amount = this.props.min_amount;
            var max_amount = this.props.max_amount;
            this.showPopup('VoucherRefundEditPopup', { 'order': order, 'min_amount': min_amount, 'max_amount': max_amount });
        }
    };
    Registries.Component.extend(PaymentScreen, PosResPaymentScreen);
});
