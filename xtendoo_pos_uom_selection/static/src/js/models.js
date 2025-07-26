/** @odoo-module **/

import { Product } from "@point_of_sale/app/models/product";
import { patch } from "@web/core/utils/patch";

patch(Product.prototype, {
    /**
     * Obtiene todas las unidades de medida compatibles con el producto
     * (del mismo tipo de categoría)
     */
    getCompatibleUoms() {
        if (!this.uom_id || !this.uom_id[0]) {
            return [];
        }

        // Buscar todas las UoM de la misma categoría
        const currentUom = this.pos.units_by_id[this.uom_id[0]];
        if (!currentUom || !currentUom.category_id) {
            return [];
        }

        const compatibleUoms = [];
        for (const uom of Object.values(this.pos.units_by_id)) {
            if (uom.category_id[0] === currentUom.category_id[0]) {
                compatibleUoms.push(uom);
            }
        }

        return compatibleUoms.sort((a, b) => a.name.localeCompare(b.name));
    },

    /**
     * Verifica si el producto tiene múltiples UoM disponibles
     */
    hasMultipleUoms() {
        return this.getCompatibleUoms().length > 1;
    }
});
