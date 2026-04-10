/** @odoo-module **/
/**
 * Xtendoo Cash Drawer - Parche de ControlButtons
 * Añade el botón "Abrir Cajón" en el área de botones de control del TPV.
 *
 * La llamada va al proxy Odoo (/xtendoo_cash_drawer/open), que reenvía
 * la petición al bridge desde Python. Sin CORS, sin restricciones de red.
 */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sendCashDrawerRequest, checkCashDrawerHealth } from "./cash_drawer_utils";

patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
    },

    /**
     * Devuelve true si el bridge del cajón está habilitado y configurado.
     * Controla la visibilidad del botón en la plantilla XML.
     */
    get cashDrawerConfigured() {
        const cfg = this.pos.config;
        // Compatible con nueva arquitectura (bridge_url) y campo legacy (open_url)
        return !!(cfg.cash_drawer_use_bridge && cfg.cash_drawer_bridge_url) ||
               !!(cfg.cash_drawer_open_url);
    },

    /**
     * Envía la petición de apertura del cajón directamente al bridge local.
     * Muestra notificación de éxito o error al usuario.
     */
    async openCashDrawer() {
        if (!this.cashDrawerConfigured) {
            this.notification.add(
                _t("El bridge del cajón portamonedas no está configurado en este TPV."),
                { type: "warning" }
            );
            return;
        }
        try {
            await sendCashDrawerRequest(this.pos.config);
            this.notification.add(_t("Cajón portamonedas abierto."), { type: "success" });
        } catch (err) {
            this.notification.add(
                _t("Error al abrir el cajón: ") + (err.message || String(err)),
                { type: "danger", sticky: true }
            );
            console.error("[CashDrawer] Error en la petición:", err);
        }
    },

    /**
     * Comprueba el estado del bridge y muestra notificación con el resultado.
     * Se puede llamar desde un botón secundario de diagnóstico.
     */
    async checkCashDrawerBridge() {
        const result = await checkCashDrawerHealth(this.pos.config);
        if (result.available) {
            this.notification.add(
                _t("Bridge del cajón disponible: ") + result.detail,
                { type: "success" }
            );
        } else {
            this.notification.add(
                _t("Bridge del cajón no disponible: ") + result.detail,
                { type: "warning", sticky: true }
            );
        }
    },
});
