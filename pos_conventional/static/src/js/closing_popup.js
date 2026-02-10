/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

/**
 * Componente para mostrar el desglose de movimientos de efectivo
 */
class PaymentMethodBreakdown extends Component {
    static template = "pos_conventional.PaymentMethodBreakdown";
    static props = {
        title: { type: String, optional: true },
        total_amount: { type: Number },
        transactions: { type: Array },
        currencyId: { type: Number, optional: true },
    };

    setup() {
        this.state = useState({ open: false });
    }

    toggle() {
        this.state.open = !this.state.open;
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat("es-ES", {
            style: "currency",
            currency: "EUR",
        }).format(amount);
    }
}

/**
 * Popup de cierre de sesión POS para modo no táctil
 */
export class ClosingPopup extends Component {
    static template = "pos_conventional.ClosingPopup";
    static components = { Dialog, PaymentMethodBreakdown };
    static props = {
        close: { type: Function },
        sessionId: { type: Number },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        this.state = useState({
            loading: true,
            notes: "",
            payments: {},
            sessionData: null,
            ordersDetails: { quantity: 0, amount: 0 },
            cashDetails: null,
            paymentMethods: [],
            cashMoves: [],
            currencyId: null,
        });

        onWillStart(async () => {
            await this.loadClosingData();
        });
    }

    async loadClosingData() {
        try {
            const sessionId = this.props.sessionId;

            const data = await this.orm.call(
                "pos.session",
                "get_closing_control_data",
                [sessionId]
            );

            this.state.sessionData = data;
            this.state.ordersDetails = data.orders_details || { quantity: 0, amount: 0 };
            this.state.cashDetails = data.default_cash_details || null;
            this.state.paymentMethods = data.non_cash_payment_methods || [];
            this.state.cashMoves = data.default_cash_details?.moves || [];
            this.state.currencyId = data.currency_id;

            if (this.state.cashDetails) {
                this.state.payments[this.state.cashDetails.id] = {
                    counted: "0",
                };
            }

            for (const pm of this.state.paymentMethods) {
                if (pm.type === "bank") {
                    this.state.payments[pm.id] = {
                        counted: this.formatAmount(pm.amount),
                    };
                }
            }

            this.state.loading = false;
        } catch (error) {
            console.error("Error loading closing data:", error);
            this.notification.add(
                _t("Error al cargar datos de cierre: ") + error.message,
                { type: "danger" }
            );
            this.state.loading = false;
        }
    }

    formatAmount(amount) {
        return amount.toFixed(2).replace(".", ",");
    }

    formatCurrency(amount) {
        if (typeof amount === "string") {
            amount = parseFloat(amount.replace(",", ".")) || 0;
        }
        return new Intl.NumberFormat("es-ES", {
            style: "currency",
            currency: "EUR",
        }).format(amount);
    }

    parseFloat(value) {
        if (typeof value === "number") return value;
        return parseFloat(String(value).replace(",", ".")) || 0;
    }

    get cashMoveData() {
        if (!this.state.cashMoves || this.state.cashMoves.length === 0) {
            return { total: 0, moves: [] };
        }

        const total = this.state.cashMoves.reduce((acc, move) => acc + move.amount, 0);
        const moves = this.state.cashMoves.map((move, i) => ({
            id: i,
            name: move.name,
            amount: move.amount,
        }));

        return { total, moves };
    }

    getDifference(paymentId) {
        const payment = this.state.payments[paymentId];
        if (!payment) return 0;

        const counted = this.parseFloat(payment.counted);

        let expectedAmount = 0;
        if (this.state.cashDetails && paymentId === this.state.cashDetails.id) {
            expectedAmount = this.state.cashDetails.amount;
        } else {
            const pm = this.state.paymentMethods.find((p) => p.id === paymentId);
            if (pm) {
                expectedAmount = pm.amount;
            }
        }

        return counted - expectedAmount;
    }

    autoFillCashCount() {
        if (this.state.cashDetails) {
            this.state.payments[this.state.cashDetails.id].counted =
                this.formatAmount(this.state.cashDetails.amount);
        }
    }

    autoFillPMCount(paymentId) {
        const pm = this.state.paymentMethods.find((p) => p.id === paymentId);
        if (pm) {
            this.state.payments[paymentId].counted = this.formatAmount(pm.amount);
        }
    }

    onCashInputChange(event) {
        const paymentId = this.state.cashDetails?.id;
        if (paymentId) {
            this.state.payments[paymentId].counted = event.target.value;
        }
    }

    onPMInputChange(paymentId, event) {
        if (this.state.payments[paymentId]) {
            this.state.payments[paymentId].counted = event.target.value;
        }
    }

    async confirm() {
        try {
            const sessionId = this.props.sessionId;

            let countedCash = 0;
            if (this.state.cashDetails) {
                countedCash = this.parseFloat(
                    this.state.payments[this.state.cashDetails.id]?.counted || "0"
                );
            }

            await this.orm.call(
                "pos.session",
                "post_closing_cash_details",
                [sessionId],
                { counted_cash: countedCash }
            );

            await this.orm.call(
                "pos.session",
                "update_closing_control_state_session",
                [sessionId, this.state.notes]
            );

            const bankPaymentMethodDiffPairs = this.state.paymentMethods
                .filter((pm) => pm.type === "bank")
                .map((pm) => [pm.id, this.getDifference(pm.id)]);

            const result = await this.orm.call(
                "pos.session",
                "close_session_from_ui",
                [sessionId, bankPaymentMethodDiffPairs]
            );

            if (result.successful === false) {
                this.notification.add(result.message || _t("Error al cerrar sesión"), {
                    type: "danger",
                });
                return;
            }

            this.notification.add(_t("Sesión cerrada correctamente"), {
                type: "success",
            });

            this.props.close();

        } catch (error) {
            console.error("Error closing session:", error);
            this.notification.add(
                _t("Error al cerrar la sesión: ") + (error.message || error.data?.message || "Error desconocido"),
                { type: "danger" }
            );
        }
    }

    cancel() {
        this.props.close();
    }

    async cashMove() {
        // Importar dinámicamente el CashMovePopup para evitar dependencias circulares
        const { CashMovePopup } = await import("./cash_move_popup");

        // Abrir el popup de entrada/salida de efectivo usando el servicio dialog
        this.dialog.add(CashMovePopup, {
            sessionId: this.props.sessionId,
            close: () => {
                // Recargar los datos de cierre para actualizar los movimientos
                this.loadClosingData();
            },
        });
    }

    async downloadSalesReport() {
        try {
            await this.action.doAction({
                type: "ir.actions.report",
                report_type: "qweb-pdf",
                report_name: "point_of_sale.report_saledetails",
                report_file: "point_of_sale.report_saledetails",
                data: { date_start: false, date_stop: false, config_ids: [] },
                context: { active_ids: [this.props.sessionId] },
            });
        } catch (error) {
            console.error("Error downloading report:", error);
            this.notification.add(
                _t("Error al descargar el reporte"),
                { type: "warning" }
            );
        }
    }
}

/**
 * Acción cliente para abrir el popup de cierre usando el servicio dialog
 */
class ClosingPopupAction extends Component {
    static template = "pos_conventional.ClosingPopupAction";
    static props = { ...standardActionServiceProps };

    setup() {
        this.dialog = useService("dialog");
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");

        onMounted(async () => {
            await this.openPopup();
        });
    }

    async openPopup() {
        try {
            const context = this.props.action?.context || {};
            let sessionId = context.session_id || context.default_session_id;

            if (!sessionId) {
                const sessions = await this.orm.searchRead(
                    "pos.session",
                    [
                        ["state", "in", ["opened", "closing_control"]],
                        ["config_id.pos_non_touch", "=", true],
                    ],
                    ["id", "name"],
                    { limit: 1, order: "id desc" }
                );

                if (sessions.length > 0) {
                    sessionId = sessions[0].id;
                }
            }

            if (!sessionId) {
                this.notification.add(_t("No se encontró ninguna sesión POS abierta."), {
                    type: "danger",
                });
                return;
            }

            // Abrir el popup usando el servicio dialog
            this.dialog.add(ClosingPopup, {
                sessionId: sessionId,
                close: () => {
                    // Al cerrar el popup, volver al tablero
                    this.action.doAction("point_of_sale.action_pos_config_kanban");
                },
            });

        } catch (error) {
            console.error("Error opening closing popup:", error);
            this.notification.add(_t("Error al abrir el popup de cierre"), { type: "danger" });
        }
    }
}

// Registrar la acción cliente
registry.category("actions").add("pos_conventional_closing_popup", ClosingPopupAction);

