/** @odoo-module **/
/**
 * Xtendoo Cash Drawer - Apertura automática en pago con efectivo.
 *
 * Parcha PaymentScreen.validateOrder para que, tras una validación exitosa
 * de un pedido con al menos un pago con método de tipo efectivo
 * (is_cash_count === true), se envíe automáticamente la señal de apertura
 * del cajón portamonedas directamente al bridge local.
 *
 * La apertura sólo se ejecuta cuando:
 *  1. El pedido quedó en estado "paid" (validación completada con éxito).
 *  2. Al menos uno de los pagos usa un método de tipo efectivo (is_cash_count).
 *  3. cash_drawer_auto_open está activo en la configuración del TPV.
 *  4. El bridge está habilitado y tiene URL configurada.
 *
 * Tolerancia a fallos:
 *  Los errores de apertura se registran en consola y se muestran como
 *  notificación de advertencia, sin interrumpir el flujo normal del TPV.
 *  El cobro siempre se completa independientemente del estado del cajón.
 */

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { _t } from "@web/core/l10n/translation";
import { sendCashDrawerRequest } from "./cash_drawer_utils";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this._cashDrawerNotification = useService("notification");
    },

    /**
     * Extiende validateOrder para abrir el cajón automáticamente si el pedido
     * se paga con efectivo y la configuración lo permite.
     *
     * La apertura se lanza en background (sin await en el resultado final)
     * para no bloquear el flujo del TPV en caso de que el bridge tarde o falle.
     *
     * @param {boolean} isForceValidate
     */
    async validateOrder(isForceValidate) {
        const order = this.currentOrder;
        // Capturamos ANTES de super para tener los datos incluso si el pedido
        // cambia de estado durante la validación.
        const hasCashPayment = _orderHasCashPayment(order);
        const cfg = this.pos.config;
        const autoOpen = cfg.cash_drawer_auto_open;
        // Soportamos tanto la nueva arquitectura como el campo legacy
        const bridgeReady = (cfg.cash_drawer_use_bridge && cfg.cash_drawer_bridge_url) ||
                            cfg.cash_drawer_open_url;

        await super.validateOrder(isForceValidate);

        // Solo abrimos si el pedido quedó pagado y se cumplen todas las condiciones
        if (hasCashPayment && autoOpen && bridgeReady && order?.finalized) {
            // Fire-and-forget: el cajón se abre sin bloquear la UI
            sendCashDrawerRequest(cfg)
                .then((result) => {
                    if (!result.ok) {
                        console.warn(
                            "[CashDrawer] Auto-apertura: respuesta negativa:",
                            result
                        );
                        this._cashDrawerNotification?.add(
                            _t("No se pudo abrir el cajón automáticamente."),
                            { type: "warning" }
                        );
                    }
                })
                .catch((err) => {
                    // El error se muestra como aviso, nunca interrumpe la sesión POS
                    console.warn("[CashDrawer] Auto-apertura falló:", err.message || err);
                    this._cashDrawerNotification?.add(
                        _t("No se pudo abrir el cajón: ") + (err.message || String(err)),
                        { type: "warning" }
                    );
                });
        }
    },
});

/**
 * Comprueba si el pedido tiene al menos un pago con método de efectivo.
 *
 * @param {object} order - Pedido POS activo
 * @returns {boolean}
 */
function _orderHasCashPayment(order) {
    if (!order) return false;
    const lines = order.payment_ids || [];
    return lines.some((line) => line.payment_method_id?.is_cash_count);
}
