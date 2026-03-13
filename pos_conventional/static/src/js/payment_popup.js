import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, onWillStart, onMounted, useExternalListener } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

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
            orderData: null,
            payments: [], // Local payment state
            selectedPaymentId: null,
            inputBuffer: "",
            overwrite: false,
            printInvoice: false,
            loading: true,
        });

        useExternalListener(window, "keydown", this.handleKeydown.bind(this));

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
            console.log("PaymentPopup OrderData:", data);
            this.state.orderData = data;

            // Initialize local payments from backend data
            if (data.payments) {
                this.state.payments = data.payments.map(p => ({
                    id: p.id,
                    payment_method_id: p.payment_method_id,
                    payment_method_name: p.payment_method_name,
                    amount: p.amount,
                }));
            }

            // Select last payment if exists
            if (this.state.payments.length > 0) {
                this.selectPayment(this.state.payments[this.state.payments.length - 1]);
            }
            this.state.loading = false;

        } catch (error) {
            console.error("Error loading order data:", error);
            this.notification.add(_t("Error al cargar datos del pedido"), { type: "danger" });
            this.state.loading = false;
        }
    }

    get amountDue() {
        if (!this.state.orderData) return 0;
        const total = this.state.orderData.amount_total || 0;
        const paid = this.state.payments.reduce((sum, p) => sum + p.amount, 0);
        // Round to avoid floating point issues (e.g. -0.00000001)
        const due = parseFloat((total - paid).toFixed(2));
        // Treat -0.00 as 0
        return Math.abs(due) < 0.001 ? 0 : due;
    }

    get amountDueLabel() {
        return this.amountDue < 0 ? _t("Cambio") : _t("Total a Pagar");
    }

    get absoluteAmountDue() {
        return Math.abs(this.amountDue);
    }

    // Proxy orderData to include local payments for XML compatibility
    get orderDataProxy() {
        if (!this.state.orderData) return null;
        return {
            ...this.state.orderData,
            payments: this.state.payments,
            amount_due: this.amountDue // Override due amount
        };
    }

    formatCurrency(amount) {
        if (!this.state.orderData) return (amount || 0).toFixed(2);
        return new Intl.NumberFormat("es-ES", {
            style: "currency",
            currency: "EUR",
        }).format(amount).replace("EUR", this.state.orderData.currency_symbol || "€");
    }

    togglePrintInvoice() {
        this.state.printInvoice = !this.state.printInvoice;
    }

    selectPayment(payment) {
        this.state.selectedPaymentId = payment.id;
        this.state.overwrite = true;
        this.state.inputBuffer = payment.amount.toFixed(2).replace(".", ",");
        if (this.state.inputBuffer.endsWith(",00")) {
             this.state.inputBuffer = this.state.inputBuffer.substring(0, this.state.inputBuffer.length - 3);
        }
    }

    handleKeydown(ev) {
        if (this.state.loading) return;
        if (ev.target.tagName === "INPUT" || ev.target.tagName === "TEXTAREA") return;

        const key = ev.key;
        console.log("Key pressed:", key); // Debug

        if (/^[0-9]$/.test(key)) {
            this.handleInput(key);
            ev.preventDefault();
            ev.stopPropagation();
        } else if (key === "," || key === ".") {
            this.handleInput(",");
            ev.preventDefault();
            ev.stopPropagation();
        } else if (key === "Backspace") {
            this.handleBackspace();
            ev.preventDefault();
            ev.stopPropagation();
        } else if (key === "Enter") {
             this.validate();
             ev.preventDefault();
             ev.stopPropagation();
        }
    }

    handleInput(char) {
        if (!this.state.selectedPaymentId) return;

        let newBuffer = this.state.inputBuffer;

        // Overwrite logic when starting to type on a selected payment
        if (this.state.overwrite) {
            this.state.overwrite = false;
            if (/^[0-9]$/.test(char)) {
                newBuffer = char;
            } else if (char === ",") {
                newBuffer = "0,";
            }
        } else {
            // Standard append logic
            if (newBuffer === "0" && char !== ",") {
                newBuffer = char;
            } else {
                if (char === "," && newBuffer.includes(",")) return;
                newBuffer += char;
            }
        }

        // Validate format (max 2 decimals)
        const parts = newBuffer.split(",");
        if (parts.length > 1 && parts[1].length > 2) {
            return;
        }

        console.log("New Buffer:", newBuffer); // Debug
        this.updatePaymentFromBuffer(newBuffer);
    }

    handleBackspace() {
        if (!this.state.selectedPaymentId) return;

        // Disable overwrite on backspace
        if (this.state.overwrite) {
            this.state.overwrite = false;
        }

        let newBuffer = this.state.inputBuffer;
        if (newBuffer.length > 0) {
            newBuffer = newBuffer.slice(0, -1);
            if (newBuffer === "") newBuffer = "0";
            this.updatePaymentFromBuffer(newBuffer);
        }
    }

    updatePaymentFromBuffer(newBuffer) {
        this.state.inputBuffer = newBuffer;
        const amount = parseFloat(newBuffer.replace(",", ".")) || 0;
        const payment = this.state.payments.find(p => p.id === this.state.selectedPaymentId);
        if (payment) {
            payment.amount = amount;
        }
    }

    addPayment(methodId) {
        // Find method details needed for display
        const method = this.state.orderData.available_methods.find(m => m.id === methodId);
        if (!method) return;

        // Determine clear ID (string to differentiate from server IDs)
        const newId = "new_" + Date.now();

        // Calculate default amount
        const initialAmount = this.amountDue;

        const newPayment = {
            id: newId,
            payment_method_id: method.id,
            payment_method_name: method.name,
            icon: method.icon,
            amount: initialAmount,
        };

        this.state.payments.push(newPayment);
        // FORCE selection update
        this.selectPayment(newPayment);

        // FORCE buffer reset if amount is 0
        if (initialAmount === 0) {
            this.state.inputBuffer = ""; // Empty buffer for typing
        }
    }

    removePayment(paymentId) {
        // Filter out payment
        this.state.payments = this.state.payments.filter(p => p.id !== paymentId);

        // If removed selected, deselect or select another
        if (this.state.selectedPaymentId === paymentId) {
            this.state.selectedPaymentId = null;
            this.state.inputBuffer = "";
            if (this.state.payments.length > 0) {
                this.selectPayment(this.state.payments[this.state.payments.length - 1]);
            }
        }
    }

    async validate(printInvoice = false) {
        // Warning if amount due is positive (not fully paid)
        // If amount due is negative (change to return), it's allowed.
        if (this.amountDue > 0.01) {
            this.notification.add(_t("Falta importe por pagar"), { type: "warning" });
             return;
        }

        const payload = this.state.payments.map(p => ({
            payment_method_id: p.payment_method_id,
            amount: p.amount
        }));

        try {
            this.state.loading = true;
            const result = await this.orm.call(
                "pos.order",
                "action_register_payments_and_validate",
                [this.props.orderId, payload, printInvoice]
            );

            if (result.success) {
                this.props.close();

                if (result.action) {
                     if (!printInvoice && result.action.params && result.action.params.next_action) {
                         await this.action.doAction(result.action.params.next_action);
                     } else {
                         await this.action.doAction(result.action);
                     }
                } else {
                     location.reload(); // Fallback
                }
            } else {
                 this.notification.add(result.message || _t("Error al validar"), { type: "danger" });
                 this.state.loading = false;
                 // Reload data to resync?
            }
        } catch (error) {
             console.error("Validation error:", error);
             const msg = (error.data && error.data.message) || error.message || "Unknown error";
             this.notification.add(_t("Error de validación: ") + msg, { type: "danger" });
             this.state.loading = false;
        }
    }

    cancel() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'pos.order',
            res_id: this.props.orderId,
            views: [[false, 'form']],
            target: 'current',
        });
        this.props.close();
    }
}

class PaymentPopupAction extends Component {
    static template = "pos_conventional.PaymentPopupAction";
    static props = { ...standardActionServiceProps };

    setup() {
        this.dialog = useService("dialog");
        this.action = useService("action");
        this.notification = useService("notification");

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
