/** @odoo-module */
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                qty_int: { type: Number, optional: true },
            },
        },
    },
    setup() {
        this._super();
        console.log("qty_int value:", this.props.line.qty_int);
    },
});
