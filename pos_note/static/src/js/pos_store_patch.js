/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { CustomLineInfoPopup } from "./custom_line_info_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

/**
 * Patch del PosStore para interceptar la adición de productos
 * que requieren información personalizada (nombre y precio por línea).
 */
patch(PosStore.prototype, {
    /**
     * Override de addLineToCurrentOrder para verificar si el producto
     * requiere información personalizada antes de añadirlo.
     */
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        // Obtener el product template
        let productTemplate = vals.product_tmpl_id;

        // Si es un ID, obtener el objeto
        if (typeof productTemplate === "number") {
            productTemplate = this.data.models["product.template"].get(productTemplate);
        }

        // Verificar si el producto requiere información personalizada
        if (productTemplate && productTemplate.pos_require_custom_info && configure) {
            // Obtener el producto para calcular el precio por defecto
            const product = productTemplate.product_variant_ids[0];
            const order = this.getOrder();
            const defaultPrice = product ? product.getPrice(
                order?.pricelist_id,
                1,
                0,
                false,
                product
            ) : 0;

            // Mostrar el popup para pedir nombre y precio personalizado
            const payload = await makeAwaitable(this.dialog, CustomLineInfoPopup, {
                title: "Información personalizada",
                productName: productTemplate.name || "",
                defaultPrice: defaultPrice,
            });

            // Si el usuario canceló, no añadir la línea
            if (!payload) {
                return;
            }

            // Añadir precio personalizado a los valores
            vals.price_unit = payload.customPrice;
            vals.price_type = "manual";
            // Pasar el nombre como full_product_name para persistencia
            vals.full_product_name = payload.customName;

            // Llamar al método original con los valores modificados
            // Usar configure=false para que no vuelva a pedir configuración
            const line = await super.addLineToCurrentOrder(vals, opts, false);

            // IMPORTANTE: Establecer los campos personalizados
            // Primero intentamos con update(), si no funciona, asignación directa
            if (line) {
                try {
                    line.update({
                        custom_line_name: payload.customName,
                        custom_line_price: payload.customPrice,
                        full_product_name: payload.customName,
                    });
                } catch (e) {
                    // Fallback: asignación directa
                    line.custom_line_name = payload.customName;
                    line.custom_line_price = payload.customPrice;
                    line.full_product_name = payload.customName;
                }
            }

            return line;
        }

        // Si no requiere info personalizada, comportamiento normal
        return super.addLineToCurrentOrder(vals, opts, configure);
    },
});
