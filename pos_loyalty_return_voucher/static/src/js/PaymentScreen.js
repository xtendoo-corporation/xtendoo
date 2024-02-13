/** @odoo-module **/

import PaymentScreen from 'point_of_sale.PaymentScreen';
import Registries from 'point_of_sale.Registries';
import session from 'web.session';

export const PosLoyaltyPaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
        /**
         * @override
         */
        async _postPushOrderResolve(order, server_ids) {
            order.loyalty_card = "";
            try {
                const loyalty_card = await this.rpc({
                    model: "pos.order",
                    method: "get_loyalty_card_from_order",
                    args: [server_ids],
                    kwargs: {context: session.user_context},
                });

                console.log("loyalty_card", loyalty_card);

                if (loyalty_card) {
                    order.loyalty_card = loyalty_card;
                }
            } finally {
                return super._postPushOrderResolve(...arguments);
            }
        }
    };

Registries.Component.extend(PaymentScreen, PosLoyaltyPaymentScreen);

