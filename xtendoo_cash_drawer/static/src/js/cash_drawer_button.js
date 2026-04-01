/** @odoo-module **/
/**
 * Xtendoo Cash Drawer - Parche de ControlButtons
 * Añade el botón "Abrir Cajón" en el área de botones de control del TPV.
 */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sendCashDrawerRequest } from "./cash_drawer_utils";

patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
    },

    /** Devuelve true si el cajón tiene URL configurada. */
    get cashDrawerUrlConfigured() {
        return !!this.pos.config.cash_drawer_open_url;
    },

    /** Envía la petición de apertura del cajón usando la URL y API key configurados. */
    async openCashDrawerUrl() {
        const baseUrl = this.pos.config.cash_drawer_open_url;
        if (!baseUrl) {
            this.notification.add(
                _t("No hay URL configurada para el cajón portamonedas."),
                { type: "warning" }
            );
            return;
        }
        try {
            await sendCashDrawerRequest(baseUrl, this.pos.config.cash_drawer_api_key);
            this.notification.add(_t("Señal de apertura del cajón enviada."), { type: "success" });
        } catch (err) {
            this.notification.add(
                _t("Error al abrir el cajón: ") + (err.message || String(err)),
                { type: "danger", sticky: true }
            );
            console.error("[CashDrawer] Error en la petición:", err);
        }
    },
});
