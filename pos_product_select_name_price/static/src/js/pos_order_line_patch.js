/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { constructAttributeString } from "@point_of_sale/utils";

/**
 * Patch de PosOrderline para manejar los campos personalizados
 * custom_line_name y custom_line_price
 */
patch(PosOrderline.prototype, {
    /**
     * Override getFullProductName para devolver el nombre personalizado si existe
     */
    getFullProductName() {
        if (this.custom_line_name) {
            return this.custom_line_name;
        }
        return this.full_product_name || this.product_id.display_name;
    },

    /**
     * Override del getter orderDisplayProductName para que muestre el nombre
     * personalizado en la pantalla del POS (modo display)
     * Este es el que realmente muestra el nombre en la lista de líneas
     */
    get orderDisplayProductName() {
        if (this.custom_line_name) {
            return {
                name: this.custom_line_name,
                attributeString: "",
            };
        }
        // Comportamiento original
        return {
            name: this.product_id?.name,
            attributeString: constructAttributeString(this),
        };
    },

    /**
     * Override canBeMergedWith para evitar merge de líneas con info personalizada
     */
    canBeMergedWith(orderline) {
        if (this.custom_line_name || orderline.custom_line_name) {
            return false;
        }
        if (this.custom_line_price || orderline.custom_line_price) {
            return false;
        }
        return super.canBeMergedWith(orderline);
    },
});
