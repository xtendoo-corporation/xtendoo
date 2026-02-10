/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

/**
 * Popup de entrada/salida de efectivo para modo no táctil (backend)
 * Basado en el CashMovePopup original de Odoo
 */
export class CashMovePopup extends Component {
    static template = "pos_conventional.CashMovePopup";
    static components = { Dialog };
    static props = {
        close: { type: Function },
        sessionId: { type: Number },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");

        this.state = useState({
            type: "out",
            amount: "",
            reason: "",
            loading: false,
            currencySymbol: "€",
            currencyPosition: "after",
        });

        onWillStart(async () => {
            await this.loadCurrencyInfo();
        });
    }

    async loadCurrencyInfo() {
        try {
            // Obtener información de la moneda de la sesión
            const sessionData = await this.orm.read(
                "pos.session",
                [this.props.sessionId],
                ["currency_id"]
            );

            if (sessionData.length > 0 && sessionData[0].currency_id) {
                const currencyId = sessionData[0].currency_id[0];
                const currencyData = await this.orm.read(
                    "res.currency",
                    [currencyId],
                    ["symbol", "position"]
                );

                if (currencyData.length > 0) {
                    this.state.currencySymbol = currencyData[0].symbol || "€";
                    this.state.currencyPosition = currencyData[0].position || "after";
                }
            }
        } catch (error) {
            console.error("Error loading currency info:", error);
        }
    }

    parseFloat(value) {
        if (typeof value === "number") return value;
        // Reemplazar coma por punto para parsear correctamente
        return parseFloat(String(value).replace(",", ".")) || 0;
    }

    formatCurrency(amount) {
        const num = this.parseFloat(amount);
        const formatted = num.toFixed(2).replace(".", ",");

        if (this.state.currencyPosition === "before") {
            return `${this.state.currencySymbol} ${formatted}`;
        }
        return `${formatted} ${this.state.currencySymbol}`;
    }

    isValidFloat(value) {
        if (!value || value === "") return false;
        const parsed = this.parseFloat(value);
        return !isNaN(parsed) && parsed > 0;
    }

    isValidCashMove() {
        return this.isValidFloat(this.state.amount) && this.state.reason.trim() !== "";
    }

    onClickButton(type) {
        this.state.type = type;
    }

    async confirm() {
        if (!this.isValidCashMove()) {
            this.notification.add(_t("Por favor, introduce un importe válido y un motivo."), {
                type: "warning",
            });
            return;
        }

        this.state.loading = true;

        try {
            const amount = this.parseFloat(this.state.amount);
            const formattedAmount = this.formatCurrency(amount);
            const type = this.state.type;
            const reason = this.state.reason.trim();

            // Llamar al método del backend para registrar el movimiento de efectivo
            await this.orm.call(
                "pos.session",
                "try_cash_in_out",
                [
                    [this.props.sessionId],
                    type,
                    amount,
                    reason,
                    false, // partnerId (no necesario en backend)
                    { formattedAmount, translatedType: type === "in" ? _t("in") : _t("out") },
                ]
            );

            this.notification.add(
                _t("Movimiento de efectivo registrado: %s %s", type === "in" ? "Entrada" : "Salida", formattedAmount),
                { type: "success" }
            );

            this.props.close();

        } catch (error) {
            console.error("Error en movimiento de efectivo:", error);
            this.notification.add(
                _t("Error al registrar el movimiento: ") + (error.message || error.data?.message || "Error desconocido"),
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    async openDetails() {
        try {
            // Obtener lista de movimientos de efectivo
            const cashMoves = await this.orm.call(
                "pos.session",
                "get_cash_in_out_list",
                [this.props.sessionId]
            );

            // Mostrar los movimientos en un diálogo simple
            let message = "";
            if (cashMoves && cashMoves.length > 0) {
                message = cashMoves.map(move => {
                    const date = new Date(move.date).toLocaleString();
                    const amount = this.formatCurrency(move.amount);
                    return `${date}: ${move.name} - ${amount}`;
                }).join("\n");
            } else {
                message = _t("No hay movimientos de efectivo registrados.");
            }

            this.notification.add(message, { type: "info", sticky: true });

        } catch (error) {
            console.error("Error al obtener movimientos:", error);
            this.notification.add(
                _t("Error al obtener los movimientos de efectivo"),
                { type: "danger" }
            );
        }
    }
}

/**
 * Acción cliente que abre el popup usando el servicio dialog
 */
class CashMovePopupAction extends Component {
    static template = "pos_conventional.CashMovePopupAction";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
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
                history.back();
                return;
            }

            // Abrir el popup usando el servicio dialog
            this.dialog.add(CashMovePopup, {
                sessionId: sessionId,
                close: () => {
                    // Simplemente volver atrás en el historial
                    history.back();
                },
            });

        } catch (error) {
            console.error("Error opening cash move popup:", error);
            this.notification.add(_t("Error al abrir el popup"), { type: "danger" });
            history.back();
        }
    }
}

// Registrar la acción cliente
registry.category("actions").add("pos_conventional_cash_move_popup", CashMovePopupAction);
