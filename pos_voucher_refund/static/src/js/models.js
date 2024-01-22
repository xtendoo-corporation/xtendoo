/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

odoo.define("pos_voucher_refund.models", function (require) {
    "use strict";

    var { PosGlobalState, Order } = require("point_of_sale.models");
    var rpc = require('web.rpc')
    const Registries = require('point_of_sale.Registries');
    var core = require('web.core');
    var QWeb = core.qweb;

    const PosRefundGlobalState = (PosGlobalState) => class PosRefundGlobalState extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            var self = this;
            $.blockUI({ message: '<h1 style="color: #c9d0d6;"><i class="fa fa-lock"></i> Screen Locked...</h1><center><p style="color: #f0f8ff;">Loading Coupons Settings..</p></center>' });
            rpc.query({
                model: 'pos.order',
                method: 'get_coupon_settings',
                args: []
            }).catch(function (unused, event) {
                event.preventDefault();
            }).then(function (voucher_configs) {
                $.unblockUI();
                self.db.voucher_configured_product_id = voucher_configs.voucher_creation_product;
            });
        }
        _save_to_server(orders, options) {
            var self = this;
            var receipt = self.get_order().export_for_printing();
            return super._save_to_server(orders, options).then(function (return_dict) {
                if (return_dict) {
                    if (self.config.iface_print_via_proxy) {
                        setTimeout(function () {
                            if (return_dict.voucher_ids) {
                                return_dict.voucher_ids.forEach(function (v_id) {
                                    rpc.query({
                                        model: 'voucher.voucher',
                                        method: 'get_coupon_data',
                                        args: [v_id],
                                    })
                                        .then(function (result) {
                                            receipt['coupon'] = result;
                                            var t = QWeb.render('CouponXmlReceipt', {
                                                receipt: receipt,
                                                widget: self,
                                            });
                                            self.proxy.print_receipt(t);
                                        });
                                });
                                delete return_dict.voucher_ids
                            }
                        }, 1500);
                    } else {
                        if (return_dict.voucher_ids) {
                            var voucher_ids = return_dict.voucher_ids;
                            delete return_dict.voucher_ids
                            voucher_ids.forEach(function (v_id) {
                                setTimeout(function () {
                                    self.env.legacyActionManager.do_action('wk_coupons.coupons_report', {
                                        additional_context: {
                                            active_ids: [v_id],
                                        }
                                    })
                                        .then(function () {
                                            if (return_dict && Object.keys(return_dict).length == 1 && return_dict.order_ids) {
                                                return return_dict.order_ids
                                            }
                                            else
                                                return return_dict
                                        })
                                }, 1500);

                            });
                        }
                    }
                }
                if (return_dict && Object.keys(return_dict).length == 1 && return_dict.order_ids) {
                    return return_dict.order_ids
                }
                else
                    return return_dict
            });
        }
    }
    Registries.Model.extend(PosGlobalState, PosRefundGlobalState);

    const PosOrder = (Order) => class PosOrder extends Order {
        constructor() {
            var res = super(...arguments);
            console.log(res)
            // var res = super.initialize();
            this.to_voucher_refund = false;
            this.refund_voucher_amount = 0.0;
            // if (options.json) {
            this.to_voucher_refund = this.to_voucher_refund;
            this.refund_voucher_amount = this.refund_voucher_amount;
            // }
            return res
        }
        is_to_voucher_refund() {
            return this.to_voucher_refund;
        }
        set_to_voucher_refund(to_voucher_refund) {
            this.assert_editable();
            this.to_voucher_refund = to_voucher_refund;
        }
        export_as_JSON() {
            var dict = super.export_as_JSON();
            dict.to_voucher_refund = this.to_voucher_refund;
            dict.refund_voucher_amount = this.refund_voucher_amount;
            return dict;
        }
    }
    Registries.Model.extend(Order, PosOrder);
});