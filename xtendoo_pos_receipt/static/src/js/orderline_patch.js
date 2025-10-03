/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";

patch(Orderline.prototype, {
    get line() {
        const line = super.line || this.props.line;
        const qty = line.qty || 0;

        // Formatear cantidad: sin decimales si es entero
        const qtyFormatted = qty % 1 === 0 ? Math.floor(qty).toString() : qty.toString();

        return {
            ...line,
            qty: qtyFormatted
        };
    }
});
