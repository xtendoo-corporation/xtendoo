odoo.define("pos_loyalty_return_voucher.ReturnVoucherScreen", function (require) {
    "use strict";

    const PaymentScreen = require("point_of_sale.PaymentScreen");
    const Registries = require("point_of_sale.Registries");

    const ReturnVoucherScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            async addNewPaymentLine({detail: paymentMethod}) {
//                const prevPaymentLines = this.currentOrder.paymentlines;
//                let res = false;
//                if (paymentMethod.used_for_loyalty_program && this.currentOrder.get_due() > 0) {
//                    this.showPopup("ErrorPopup", {
//                        title: this.env._t("Error"),
//                        body: this.env._t("This is a loyalty program, only for refund voucher"),
//                    });
//                    return false;
//                }
                let data = super.addNewPaymentLine(...arguments);
                alert(data);
                return data;
            }
        };

    Registries.Component.extend(PaymentScreen, ReturnVoucherScreen);

    return PaymentScreen;
});
