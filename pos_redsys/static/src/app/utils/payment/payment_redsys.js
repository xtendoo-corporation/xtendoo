import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";

const REQUEST_TIMEOUT_MS = 120000;

export class PaymentRedsys extends PaymentInterface {
    sendPaymentRequest(uuid) {
        super.sendPaymentRequest(uuid);
        return this._redsysPay(uuid);
    }

    sendPaymentCancel(order, uuid) {
        super.sendPaymentCancel(order, uuid);
        return this._redsysCancel();
    }

    /**
     * TODO: the request/response contract with the TPV-PC is a placeholder.
     * Adapt it to the Redsys TPV-PC documentation (canales.redsys.es > documentación).
     */
    async _callAgent(operation, payload) {
        const method = this.payment_method_id;
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
        try {
            const response = await fetch(`${method.redsys_agent_url}/${operation}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    merchantCode: method.redsys_merchant_code,
                    terminal: method.redsys_terminal_number,
                    testMode: method.redsys_test_mode,
                    ...payload,
                }),
                signal: controller.signal,
            });
            return await response.json();
        } catch {
            this._showError(
                _t("Could not connect to the Redsys TPV-PC. Check that it is running on this computer.")
            );
            return null;
        } finally {
            clearTimeout(timer);
        }
    }

    async _redsysPay(uuid) {
        const order = this.pos.getOrder();
        const line = order.payment_ids.find((paymentLine) => paymentLine.uuid === uuid);
        if (line.amount < 0) {
            this._showError(_t("Refunds are not supported yet."));
            return false;
        }
        line.setPaymentStatus("waitingCard");
        const result = await this._callAgent("payment", {
            orderId: order.uuid,
            amount: line.amount,
            currency: this.pos.currency.name,
        });
        // Expected (placeholder): { approved: bool, transactionId, cardType, message }
        if (!result?.approved) {
            if (result?.message) {
                this._showError(_t("Message from Redsys: %s", result.message));
            }
            return false;
        }
        line.transaction_id = result.transactionId;
        line.card_type = result.cardType;
        return true;
    }

    async _redsysCancel() {
        await this._callAgent("cancel", {});
        return true;
    }

    _showError(body) {
        this.env.services.dialog.add(AlertDialog, { title: _t("Redsys Error"), body });
    }
}

register_payment_method("redsys", PaymentRedsys);
