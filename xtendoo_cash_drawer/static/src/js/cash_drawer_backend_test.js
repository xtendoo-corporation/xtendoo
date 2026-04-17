/** @odoo-module **/
/**
 * Acción cliente para probar la apertura del cajón portamonedas.
 *
 * Se ha simplificado para realizar la apertura DIRECTA por petición del usuario,
 * eliminando el diálogo intermedio tanto en el TPV como en Ajustes.
 */
import { registry } from "@web/core/registry";
import { sendCashDrawerRequest } from "./cash_drawer_utils";
import { _t } from "@web/core/l10n/translation";

/**
 * Registra la acción cliente en el registro de Odoo.
 *
 * Se activa cuando action_test_cash_drawer() devuelve:
 *   { type: "ir.actions.client", tag: "xtendoo_cash_drawer_open_test", params: {...} }
 */
registry.category("actions").add("xtendoo_cash_drawer_open_test", async (env, action) => {
    const params = action.params || {};
    const bridgeUrl = params.bridge_url || "";

    if (!bridgeUrl) {
        env.services.notification.add(
            _t("No hay URL del bridge configurada para el cajón portamonedas."),
            { type: "warning" }
        );
        return false;
    }

    try {
        // Ejecutamos la apertura usando la utilidad compartida
        await sendCashDrawerRequest({
            cash_drawer_bridge_url: bridgeUrl,
            cash_drawer_printer_name: params.printer_name || "",
            cash_drawer_api_key: params.api_key || "",
        });

        env.services.notification.add(_t("Señal de apertura enviada correctamente."), {
            type: "success",
        });
    } catch (err) {
        env.services.notification.add(
            _t("Error al abrir el cajón: ") + (err.message || String(err)),
            { type: "danger", sticky: true }
        );
        console.error("[CashDrawer] Error en acción de apertura:", err);
    }

    return false;
});
