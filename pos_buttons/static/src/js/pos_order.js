/** @odoo-module **/

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";


patch(Order.prototype, {

    init() {
        this._super.apply(this, arguments);
        this.to_picking = false;
        this.to_invoice = false;
    },

    is_to_picking() {
        return this.to_picking;
    },

    is_to_invoice() {
        return this.to_invoice;
    },

    set_to_picking(isToPicking) {
        this.to_picking = isToPicking;

        if (isToPicking) {
            this.set_to_invoice(false);
        }

        console.log(`Picking status updated: ${this.to_picking}`);
    },

    set_to_invoice(isToInvoice) {
        this.to_invoice = isToInvoice;

        if (isToInvoice) {
            this.set_to_picking(false);
        }

        console.log(`Invoice status updated: ${this.to_invoice}`);
    },
});
