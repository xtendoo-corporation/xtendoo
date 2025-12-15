/** @odoo-module **/
/**
 * Patch del PosStore para integrar la balanza serie
 *
 * Este patch carga la configuración del servicio de balanza serie
 * cuando el POS se inicializa y proporciona integración con productos pesables.
 */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { SerialScalePopup } from "./serial_scale_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(PosStore.prototype, {
    async setup(env, deps) {
        await super.setup(...arguments);

        // Cargar configuración del servicio de balanza serie después de la inicialización
        this._initSerialScale();
    },

    _initSerialScale() {
        try {
            const serialScale = this.env.services.serial_scale;
            if (serialScale && this.config) {
                serialScale.loadConfig(this.config);
                console.log("[PosStore] Configuración de balanza serie cargada");
            }
        } catch (error) {
            console.warn("[PosStore] No se pudo inicializar el servicio de balanza serie:", error);
        }
    },

    /**
     * Override del método para obtener peso de producto
     * Si la balanza serie está conectada, usa el popup de balanza serie
     */
    async getProductWeight(product) {
        const serialScale = this.env.services.serial_scale;

        // Si la balanza serie está habilitada y conectada, usar el popup de balanza serie
        if (serialScale &&
            serialScale.config.enabled &&
            serialScale.isConnected()) {

            return await this._getWeightFromSerialScale(product);
        }

        // Fallback al comportamiento original (IoT Box)
        if (super.getProductWeight) {
            return super.getProductWeight(product);
        }

        return null;
    },

    /**
     * Obtiene el peso desde la balanza serie mediante popup
     */
    async _getWeightFromSerialScale(product) {
        return new Promise((resolve) => {
            this.dialog.add(SerialScalePopup, {
                applyToProduct: true,
                getPayload: (weight) => {
                    resolve(weight);
                },
            });
        });
    },

    /**
     * Método para abrir el popup de balanza serie manualmente
     */
    openSerialScalePopup() {
        const serialScale = this.env.services.serial_scale;
        if (!serialScale) {
            console.warn("[PosStore] Servicio de balanza serie no disponible");
            return;
        }

        this.dialog.add(SerialScalePopup, {
            applyToProduct: false,
        });
    },
});

