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
            order.loyalty_card_code = "";
            order.loyalty_card_expiration_date = "";
            try {
                const loyalty_card_code = await this.rpc({
                    model: "pos.order",
                    method: "get_loyalty_card_code_from_order",
                    args: [server_ids],
                    kwargs: {context: session.user_context},
                });

                console.log("loyalty_card_code", loyalty_card_code);

                if (loyalty_card_code) {
                    order.loyalty_card_code = loyalty_card_code;
                }
//                if (loyalty_card_code.loyalty_card_expiration_date) {
//                    order.loyalty_card_expiration_date = loyalty_card_code.loyalty_card_expiration_date;
//                }
            } finally {
                return super._postPushOrderResolve(...arguments);
            }
        }
    };

Registries.Component.extend(PaymentScreen, PosLoyaltyPaymentScreen);

