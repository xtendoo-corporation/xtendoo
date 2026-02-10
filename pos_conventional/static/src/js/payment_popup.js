/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

/**
 * Popup de pago combinado para POS Conventional
 */
export class PaymentPopup extends Component {
    static template = "pos_conventional.PaymentPopup";
    static components = { Dialog };
    static props = {
        close: { type: Function },
        orderId: { type: Number },
        onValidate: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            orderData: {
                amount_due: 0,
                amount_total: 0,
                amount_paid: 0,
                currency_symbol: "€",
                available_methods: [],
                payments: [],
            },
            inputBuffer: "0",
            selectedMethodId: null,
            error: null,
        });

        onWillStart(async () => {
            await this.loadOrderData();
        });
    }

    async loadOrderData() {
        try {
            const data = await this.orm.call(
                "pos.order",
                "get_payment_popup_data",
                [this.props.orderId]
            );
            if (data) {
                this.state.orderData = data;
                this.state.inputBuffer = (data.amount_due || 0).toFixed(2).replace(".", ",");
                this.state.loading = false;
            } else {
                throw new Error("No data received from server");
            }
        } catch (error) {
            console.error("Error loading order data:", error);
            this.state.error = error.message || error.data?.message || _t("Error desconocido");
            this.notification.add(_t("Error al cargar datos del pedido: ") + this.state.error, { type: "danger" });
            this.state.loading = false;
        }
    }

    formatCurrency(amount) {
        if (!this.state.orderData) return amount.toFixed(2);
        return new Intl.NumberFormat("es-ES", {
            style: "currency",
            currency: "EUR", 
        }).format(amount).replace("EUR", this.state.orderData.currency_symbol || "€");
    }

    // --- Numpad Logic ---
    sendInput(key) {
        // Si el buffer es igual al total pendiente inicial, lo limpiamos al empezar a escribir
        const initialAmount = this.state.orderData.amount_due.toFixed(2).replace(".", ",");
        if (this.state.inputBuffer === initialAmount && key !== "Backspace") {
            this.state.inputBuffer = "";
        }

        if (key === "Backspace") {
            this.state.inputBuffer = this.state.inputBuffer.slice(0, -1) || "0";
        } else if (key === "," || key === ".") {
            if (!this.state.inputBuffer.includes(",")) {
                this.state.inputBuffer += ",";
            }
        } else {
            if (this.state.inputBuffer === "0") {
                this.state.inputBuffer = key;
            } else {
                this.state.inputBuffer += key;
            }
        }
    }

    onInputChange(event) {
        let value = event.target.value;
        // Solo permitir números y una coma
        value = value.replace(/[^0-9,]/g, "");
        // Asegurar una sola coma
        const parts = value.split(",");
        if (parts.length > 2) {
            value = parts[0] + "," + parts.slice(1).join("");
        }
        this.state.inputBuffer = value || "0";
    }

    get inputAmount() {
        return parseFloat(this.state.inputBuffer.replace(",", ".")) || 0;
    }


    // --- Actions ---
    async addPayment(methodId) {
        const amount = this.inputAmount;
        if (amount <= 0) {
            this.notification.add(_t("El importe debe ser mayor que 0"), { type: "warning" });
            return;
        }

        try {
            const data = await this.orm.call(
                "pos.order",
                "add_payment_from_ui",
                [this.props.orderId, methodId, amount]
            );
            this.state.orderData = data;
            this.state.inputBuffer = data.amount_due.toFixed(2).replace(".", ",");
        } catch (error) {
            console.error("Error adding payment:", error);
            this.notification.add(_t("Error al añadir pago"), { type: "danger" });
        }
    }

    async removePayment(paymentId) {
        try {
            const data = await this.orm.call(
                "pos.order",
                "remove_payment_from_ui",
                [this.props.orderId, paymentId]
            );
            this.state.orderData = data;
            this.state.inputBuffer = data.amount_due.toFixed(2).replace(".", ",");
        } catch (error) {
            console.error("Error removing payment:", error);
            this.notification.add(_t("Error al eliminar pago"), { type: "danger" });
        }
    }

    async validate() {
        if (this.state.orderData.amount_due > 0.01) {
            this.notification.add(_t("El pedido no está totalmente pagado"), { type: "warning" });
            return;
        }

        try {
            this.state.loading = true;
            const result = await this.orm.call(
                "pos.order",
                "action_validate_and_invoice",
                [this.props.orderId]
            );
            
            this.props.close();
            
            if (result && result.type === "ir.actions.client") {
                await this.action.doAction(result);
            } else if (this.props.onValidate) {
                this.props.onValidate();
            } else {
                // Refresh order view
                await this.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "pos.order",
                    res_id: this.props.orderId,
                    view_mode: "form",
                    target: "current",
                });
            }
        } catch (error) {
            console.error("Error validating order:", error);
            this.notification.add(_t("Error al validar el pedido"), { type: "danger" });
            this.state.loading = false;
        }
    }

    cancel() {
        this.props.close();
    }
}

/**
 * Acción cliente para abrir el popup de pago
 */
class PaymentPopupAction extends Component {
    static template = "pos_conventional.PaymentPopupAction";
    static props = { ...standardActionServiceProps };

    setup() {
        this.dialog = useService("dialog");
        this.action = useService("action");

        onMounted(() => {
            const context = this.props.action?.context || {};
            const orderId = context.active_id;
            if (orderId) {
                this.dialog.add(PaymentPopup, {
                    orderId: orderId,
                    close: () => {
                        this.action.doAction({ type: "ir.actions.act_window_close" });
                    },
                });
            } else {
                this.notification.add(_t("No se ha seleccionado ningún pedido."), { type: "warning" });
                this.action.doAction({ type: "ir.actions.act_window_close" });
            }
        });
    }
}

registry.category("actions").add("pos_conventional_payment_popup", PaymentPopupAction);
