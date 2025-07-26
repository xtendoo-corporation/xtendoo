/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { UomSelectionPopup } from "./UomSelectionPopup";

patch(ProductScreen.prototype, {
    /**
     * Abre el popup de selección de unidad de medición
     */
    async openUomSelection(product, orderline) {
        if (!this.pos.config.allow_uom_selection) {
            return;
        }

        const compatibleUoms = product.getCompatibleUoms();
        if (compatibleUoms.length <= 1) {
            return;
        }

        const { confirmed, payload } = await this.popup.add(UomSelectionPopup, {
            title: `Seleccionar Unidad de Medición - ${product.display_name}`,
            product: product,
            uoms: compatibleUoms,
            currentUom: orderline ? orderline.uom_id : product.uom_id[0],
        });

        if (confirmed && payload.selectedUom) {
            if (orderline) {
                // Si ya existe una línea de pedido, actualizar su UoM
                orderline.set_unit_of_measure(payload.selectedUom);
            } else {
                // Si no existe línea, crear una nueva con la UoM seleccionada
                const newOrderline = this.currentOrder.add_product(product, {
                    uom: payload.selectedUom,
                });
                return newOrderline;
            }
        }
    },

    /**
     * Maneja el clic en el botón de UoM
     */
    async onUomButtonClick(product, orderline) {
        await this.openUomSelection(product, orderline);
    },
});
