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
            alert(result.loyalty_card_code);
            console.log("result",result);
            return result;
        }
    };

Registries.Model.extend(Order, LoyaltyPaymentOrder);

export default LoyaltyPaymentOrder;

//import {Order, Payment} from "point_of_sale.models";
//import Registries from "point_of_sale.Registries";
//
//export const LoyaltyPaymentOrder = (OriginalOrder) =>
//    class extends OriginalOrder {
//        constructor(obj, options) {
//            super(obj, options);
//            this.loyalty_card_code_ids = "this.loyalty_card_code_ids || null";
//        }
//        export_as_JSON() {
//            const json = super.export_as_JSON(...arguments);
//            json.loyalty_card_code_ids = "this.loyalty_card_code_ids";
//            alert(json.loyalty_card_code_ids);
//            return json;
//        }
//        init_from_JSON(json) {
//            super.init_from_JSON(...arguments);
//            this.loyalty_card_code_ids = "json.loyalty_card_code_ids";
//            alert(this.loyalty_card_code_ids);
//        }
//        export_for_printing() {
//            const result = super.export_for_printing(...arguments);
//            result.loyalty_card_code_ids = "this.loyalty_card_code_ids";
//            return result;
//        }
//    };

//Registries.Model.extend(Order, LoyaltyPaymentOrder);
//
//    const L10NESOrder = (Order) =>
//        class L10NESOrder extends Order {
//            get_total_with_tax() {
//                const total = super.get_total_with_tax(...arguments);
//                const below_limit =
//                    total <= this.pos.config.l10n_es_simplified_invoice_limit;
//                this.is_simplified_invoice =
//                    below_limit && this.pos.config.is_simplified_config;
//                return total;
//            }
//            set_simple_inv_number() {
//                return this.pos
//                    .get_simple_inv_next_number()
//                    .then(([config]) => {
//                        // We'll get the number from DB only when we're online. Otherwise
//                        // the sequence will run on the client side until the orders are
//                        // synced.
//                        this.pos._set_simplified_invoice_number(config);
//                    })
//                    .catch((error) => {
//                        // We'll only consider network errors
//                        if (!isConnectionError(error)) {
//                            throw error;
//                        }
//                    })
//                    .finally(() => {
//                        const simplified_invoice_number =
//                            this.pos._get_simplified_invoice_number();
//                        this.l10n_es_unique_id = simplified_invoice_number;
//                        this.is_simplified_invoice = true;
//                    });
//            }
//            get_base_by_tax() {
//                const base_by_tax = {};
//                this.get_orderlines().forEach(function (line) {
//                    const tax_detail = line.get_tax_details();
//                    const base_price = line.get_price_without_tax();
//                    if (tax_detail) {
//                        Object.keys(tax_detail).forEach(function (tax) {
//                            if (Object.keys(base_by_tax).includes(tax)) {
//                                base_by_tax[tax] += base_price;
//                            } else {
//                                base_by_tax[tax] = base_price;
//                            }
//                        });
//                    }
//                });
//                return base_by_tax;
//            }
//            init_from_JSON(json) {
//                super.init_from_JSON(...arguments);
//                this.to_invoice = json.to_invoice;
//                this.l10n_es_unique_id = json.l10n_es_unique_id;
//                this.formatted_validation_date = field_utils.format.datetime(
//                    moment(this.validation_date),
//                    {},
//                    {timezone: false}
//                );
//            }
//            export_as_JSON() {
//                const res = super.export_as_JSON(...arguments);
//                res.to_invoice = this.is_to_invoice();
//                if (!res.to_invoice) {
//                    res.l10n_es_unique_id = this.l10n_es_unique_id;
//                }
//                return res;
//            }
//            export_for_printing() {
//                const result = super.export_for_printing(...arguments);
//                const company = this.pos.company;
//                result.l10n_es_unique_id = this.l10n_es_unique_id;
//                result.to_invoice = this.to_invoice;
//                result.company.street = company.street;
//                result.company.zip = company.zip;
//                result.company.city = company.city;
//                result.company.state_id = company.state_id;
//                const base_by_tax = this.get_base_by_tax();
//                for (const tax of result.tax_details) {
//                    tax.base = base_by_tax[tax.tax.id];
//                }
//                return result;
//            }
//        };
//    Registries.Model.extend(Order, L10NESOrder);
//
