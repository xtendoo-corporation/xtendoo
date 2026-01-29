/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    /**
     * @override
     * Hook que se ejecuta después de procesar los datos del servidor
     */
    async afterProcessServerData() {
        await super.afterProcessServerData(...arguments);

        // Establecer la categoría por defecto
        this._setDefaultCategory();
    },

    _setDefaultCategory() {
        try {
            if (!this.config || !this.config.default_pos_category_id) {
                return;
            }

            const defaultCategoryId = this.config.default_pos_category_id;
            let categoryId = null;

            // El campo puede ser un objeto (Many2one) o solo el ID
            if (typeof defaultCategoryId === 'object' && defaultCategoryId.id) {
                categoryId = defaultCategoryId.id;
            } else if (typeof defaultCategoryId === 'number') {
                categoryId = defaultCategoryId;
            }

            if (categoryId && this.models && this.models["pos.category"]) {
                const category = this.models["pos.category"].get(categoryId);
                if (category) {
                    this.selectedCategory = category;
                    console.log(`[POS Default Category] Categoría por defecto: ${category.name}`);
                }
            }
        } catch (error) {
            console.warn("[POS Default Category] Error:", error);
        }
    }
});
