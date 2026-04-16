/** @odoo-module **/
/**
 * Xtendoo Cash Drawer - Parche de ControlButtons
 * Añade el botón "Abrir Cajón" en el área de botones de control del TPV.
 *
 * Arquitectura: POS → método Python pos.config.action_test_cash_drawer()
 * Reutiliza exactamente la misma acción cliente que ya funciona desde la
 * configuración del TPV.
 */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { checkCashDrawerHealth } from "./cash_drawer_utils";

patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
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
     * Devuelve el ID real de pos.config en la sesión POS.
     * Soporta tanto el config cargado directamente como el M2O de la sesión.
     *
     * @returns {number|null}
     */
    get cashDrawerConfigId() {
        const configId = this.pos.config?.id;
        if (typeof configId === "number") {
            return configId;
        }
        const sessionConfigId = this.pos.pos_session?.config_id;
        if (Array.isArray(sessionConfigId)) {
            return sessionConfigId[0] || null;
        }
        return sessionConfigId || null;
    },

    /**
     * Llama al método Python action_test_cash_drawer() y ejecuta la acción
     * cliente devuelta. Así reutiliza el mismo flujo que funciona desde
     * configuración, sin duplicar la lógica en JS del botón.
     */
    async openCashDrawer() {
        if (!this.cashDrawerConfigured) {
            this.notification.add(
                _t("El bridge del cajón portamonedas no está configurado en este TPV."),
                { type: "warning" }
            );
            return;
        }
        const configId = this.cashDrawerConfigId;
        if (!configId) {
            this.notification.add(
                _t("No se pudo identificar la configuración del TPV para abrir el cajón."),
                { type: "danger", sticky: true }
            );
            return;
        }
        try {
            const action = await this.orm.call(
                "pos.config",
                "action_test_cash_drawer",
                [[configId]]
            );
            if (action) {
                await this.action.doAction(action);
            }
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
