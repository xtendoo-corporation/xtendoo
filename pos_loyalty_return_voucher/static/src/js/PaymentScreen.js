/** @odoo-module **/

import PaymentScreen from 'point_of_sale.PaymentScreen';
import Registries from 'point_of_sale.Registries';
import session from 'web.session';

export const PosLoyaltyPaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
        /**
         * @override
         */
        async validateOrder(isForceValidate) {
            await super.validateOrder(...arguments);
        }

        /**
         * @override
         */
        async _postPushOrderResolve(order, server_ids) {
            try {
                const loyalty_card_code = await this.rpc({
                    model: "pos.order",
                    method: "get_loyalty_card_code_from_order",
                    args: [server_ids],
                    kwargs: {context: session.user_context},
                });

                console.log("loyalty_card_code", loyalty_card_code);
                console.log("loyalty_card_code.code", loyalty_card_code.code);

                if (loyalty_card_code.code) {
                    order.set_loyalty_card_code(loyalty_card_code.code || "");
                }
                console.log("get_loyalty_card_code", order.get_loyalty_card_code());
            } finally {
                return super._postPushOrderResolve(...arguments);
            }
        }
    };

Registries.Component.extend(PaymentScreen, PosLoyaltyPaymentScreen);

