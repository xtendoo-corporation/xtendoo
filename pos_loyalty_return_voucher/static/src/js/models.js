/** @odoo-module **/

import {Order} from "point_of_sale.models";
import PaymentScreen from 'point_of_sale.PaymentScreen';
import Registries from "point_of_sale.Registries";

const LoyaltyPaymentOrder = (Order) =>
    class extends Order {
        constructor() {
            super(...arguments);
            console.log("this.pos", this.pos);
        }
        set_loyalty_card(loyalty_card) {
            this.loyalty_card = loyalty_card;
        }
        get_loyalty_card() {
            return this.loyalty_card;
        }
        export_as_JSON() {
            const result = super.export_as_JSON(...arguments);
            result.loyalty_card = this.loyalty_card;
            return result;
        }
        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.loyalty_card = json.loyalty_card;
        }
        export_for_printing() {
            const result = super.export_for_printing(...arguments);
            result.loyalty_card = this.get_loyalty_card();
            return result;
        }
    };

Registries.Model.extend(Order, LoyaltyPaymentOrder);

export default LoyaltyPaymentOrder;

