/** @odoo-module **/
/**
 * Xtendoo Cash Drawer - Apertura automática en pago con efectivo.
 *
 * Parcha PaymentScreen.validateOrder para que, tras una validación exitosa
 * de un pedido con al menos un pago con método de tipo efectivo
 * (is_cash_count === true), se envíe automáticamente la señal de apertura
 * del cajón portamonedas a través del proxy de Odoo.
 *
 * La apertura sólo se ejecuta cuando:
 *  1. El pedido quedó en estado "paid" (validación completada con éxito).
 *  2. Al menos uno de los pagos usa un método de tipo efectivo (is_cash_count).
 *  3. La configuración del TPV tiene una URL de apertura del cajón.
 *  4. El campo cash_drawer_auto_open está activo en la configuración del TPV.
 *
 * Los errores de apertura se registran en consola y se muestran como
 * notificación de advertencia, sin interrumpir el flujo normal del TPV.
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
     * @param {boolean} isForceValidate
     */
    async validateOrder(isForceValidate) {
        const order = this.currentOrder;

        // Capturamos el estado ANTES de llamar a super para detectar si hay
        // pagos en efectivo incluso cuando el pedido cambia de pantalla.
        const hasCashPayment = _orderHasCashPayment(order);
        const drawerUrl = this.pos.config.cash_drawer_open_url;
        const autoOpen = this.pos.config.cash_drawer_auto_open;

        await super.validateOrder(isForceValidate);

        // Verificamos que el pedido quedó efectivamente pagado antes de abrir.
        if (hasCashPayment && drawerUrl && autoOpen && order?.finalized) {
            sendCashDrawerRequest(drawerUrl, this.pos.config.cash_drawer_api_key).then(
                (result) => {
                    if (!result.success) {
                        console.warn("[CashDrawer] Auto-apertura: respuesta negativa:", result.error);
                        this._cashDrawerNotification?.add(
                            _t("No se pudo abrir el cajón automáticamente: ") + (result.error || ""),
                            { type: "warning" }
                        );
                    }
                }
            ).catch((err) => {
                console.warn("[CashDrawer] Auto-apertura falló:", err);
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

