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
        set_loyalty_card_code(loyalty_card_code) {
            console.log("set_loyalty_card_code", loyalty_card_code);
            this.loyalty_card_code = loyalty_card_code;
        }
        get_loyalty_card_code() {
            return this.loyalty_card_code;
        }
        export_as_JSON() {
            const result = super.export_as_JSON(...arguments);
            result.loyalty_card_code = this.loyalty_card_code;
            return result;
        }
        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            console.log("init from json",json);
            this.loyalty_card_code = json.loyalty_card_code;
        }
        export_for_printing() {
            const result = super.export_for_printing(...arguments);
            result.loyalty_card_code = this.get_loyalty_card_code();
            console.log("result",result);
            return result;
        }
    };

Registries.Model.extend(Order, LoyaltyPaymentOrder);

export default LoyaltyPaymentOrder;

