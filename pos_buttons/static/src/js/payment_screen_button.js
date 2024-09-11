/** @odoo-module **/

import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    async toggleIsToPicking() {
        console.log("toggleIsToPicking");
        this.currentOrder.set_to_picking(!this.currentOrder.is_to_picking());

    },

    async _finalizeValidation() {
    console.log('Starting _finalizeValidation');

    // Verifica si se debe abrir la caja registradora
    if (this.currentOrder.is_paid_with_cash() || this.currentOrder.get_change()) {
        console.log('Opening cashbox');
        this.hardwareProxy.openCashbox();
    }

    // Establece la fecha del pedido
    this.currentOrder.date_order = luxon.DateTime.now();
    console.log('Order date set to:', this.currentOrder.date_order.toISO());

    if (this.currentOrder.is_to_picking()) {
    for (const line of this.paymentLines) {
        if (line.amount !== 0) {
            console.log('Removing payment line with amount:', line.amount);
            this.currentOrder.remove_paymentline(line);
        }
    }
    }else{
     for (const line of this.paymentLines) {
        if (!line.amount === 0) {
            console.log('Removing payment line with amount:', line.amount);
            this.currentOrder.remove_paymentline(line);
        }
    }
    }

    // No marcar el pedido como finalizado si is_to_picking es true
    if (!this.currentOrder.is_to_picking()) {
        console.log('Finalizing order');
        for (const line of this.paymentLines) {
            if (!line.amount === 0) {
                this.currentOrder.remove_paymentline(line);
            }
        }
        this.currentOrder.finalized = true;
    } else {
        console.log('Order is to picking, not finalizing');
        this.currentOrder.finalized = false;
    }

    this.env.services.ui.block();
    let syncOrderResult;
    try {
        // Guardar pedido en el servidor
        console.log('Pushing order to server');
        syncOrderResult = await this.pos.push_single_order(this.currentOrder);
        console.log('Order push result:', syncOrderResult);

        if (!syncOrderResult || syncOrderResult.length === 0) {
            console.log('Sync result is null, undefined, or empty');
            return;
        }

        // Omitir la facturación si is_to_picking es true
        if (!this.currentOrder.is_to_picking()) {
            console.log('Processing invoice');
            if (this.shouldDownloadInvoice() && this.currentOrder.is_to_invoice()) {
                if (syncOrderResult[0]?.account_move) {
                    await this.report.doAction("account.account_invoices", [
                        syncOrderResult[0].account_move,
                    ]);
                } else {
                    throw {
                        code: 401,
                        message: "Backend Invoice",
                        data: { order: this.currentOrder },
                    };
                }
            }
          }
        }catch (error) {
        console.error('Error during validation:', error);
        // Manejo de error sin ConnectionLostError
        if (error.message.includes('Connection lost')) {
            console.log('Connection lost, showing next screen');
            this.pos.showScreen(this.nextScreen);
            return Promise.reject(error);
        } else {
            throw error;
        }
    } finally {
        console.log('Unblocking UI');
        this.env.services.ui.unblock();
    }

    // Post procesamiento
    if (
        syncOrderResult &&
        syncOrderResult.length > 0 &&
        this.currentOrder.wait_for_push_order()
    ) {
        console.log('Post push order resolve');
        await this.postPushOrderResolve(syncOrderResult.map((res) => res.id));
    }

    console.log('After order validation');
    await this.afterOrderValidation(!!syncOrderResult && syncOrderResult.length > 0);
}
});
