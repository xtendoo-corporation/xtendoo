/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

/**
 * Popup de apertura de caja para modo no táctil (backend)
 * Basado en el OpeningControlPopup original de Odoo
 */
export class OpeningPopup extends Component {
    static template = "pos_conventional.OpeningPopup";
    static components = { Dialog };
    static props = {
        close: { type: Function, optional: true },
        sessionId: { type: Number, optional: true },
        configId: { type: Number, optional: true },
        onOpened: { type: Function, optional: true },
        action: { type: Object, optional: true },
        actionId: { type: Number, optional: true },
        updateActionState: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");

        this.sessionId = this.props.sessionId || this.props.action?.context?.session_id;
        this.configId = this.props.configId || this.props.action?.context?.config_id;

        this.state = useState({
            loading: true,
            notes: "",
            openingCash: "0,00",
            sessionName: "",
            configName: "",
            cashControlEnabled: true,
            currencySymbol: "€",
            currencyPosition: "after",
        });

        onWillStart(async () => {
            await this.loadSessionData();
        });
    }

    async loadSessionData() {
        try {
            // Obtener datos de la sesión
            const sessionData = await this.orm.read(

                "pos.session",
                [this.sessionId],
                ["name", "config_id", "cash_register_balance_start", "state", "currency_id"]
            );

            if (sessionData.length > 0) {
                const session = sessionData[0];
                this.state.sessionName = session.name;

                // Obtener balance inicial si existe
                const balanceStart = session.cash_register_balance_start || 0;
                this.state.openingCash = this.formatAmount(balanceStart);

                // Obtener datos de la configuración
                const configId = Array.isArray(session.config_id)
                    ? session.config_id[0]
                    : session.config_id;

                const configData = await this.orm.read(
                    "pos.config",
                    [configId],
                    ["name", "cash_control"]
                );

                if (configData.length > 0) {
                    this.state.configName = configData[0].name;
                    this.state.cashControlEnabled = configData[0].cash_control;
                }

                // Obtener información de la moneda
                if (session.currency_id) {
                    const currencyId = Array.isArray(session.currency_id)
                        ? session.currency_id[0]
                        : session.currency_id;

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
            }

            this.state.loading = false;
        } catch (error) {
            console.error("Error loading session data:", error);
            this.notification.add(
                _t("Error al cargar datos de la sesión: ") + error.message,
                { type: "danger" }
            );
            this.state.loading = false;
        }
    }

    formatAmount(amount) {
        return amount.toFixed(2).replace(".", ",");
    }

    parseFloat(value) {
        if (typeof value === "number") return value;
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
        return !isNaN(parsed) && parsed >= 0;
    }

    async confirm() {
        if (this.state.cashControlEnabled && !this.isValidFloat(this.state.openingCash)) {
            this.notification.add(_t("Por favor, introduce un importe válido."), {
                type: "warning",
            });
            return;
        }

        try {
            const openingCash = this.parseFloat(this.state.openingCash);

            // Llamar al método de apertura de la sesión
            await this.orm.call(
                "pos.session",
                "set_opening_control",
                [this.sessionId, openingCash, this.state.notes]
            );

            this.notification.add(_t("Caja abierta correctamente"), {
                type: "success",
            });

            // Llamar al callback si existe
            if (this.props.onOpened) {
                this.props.onOpened();
            }

            if (this.props.close) {
                this.props.close();
            }

            // Navegar a la lista de pedidos POS con el contexto de la sesión
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "pos.order",
                name: _t("Pedidos POS"),
                view_mode: "list,form",
                views: [[false, "list"], [false, "form"]],
                target: "current",
                context: {

                    default_session_id: this.sessionId,
                    default_config_id: this.configId,
                },
            });

        } catch (error) {
            console.error("Error opening session:", error);
            this.notification.add(
                _t("Error al abrir la caja: ") + (error.message || error.data?.message || "Error desconocido"),
                { type: "danger" }
            );
        }
    }

    cancel() {
        if (this.props.close) {
            this.props.close();
        } else {
            // Cerrar la ventana de acción
            this.action.doAction({ type: "ir.actions.act_window_close" });
        }
    }

    autoFillCash() {
        // Por defecto poner 0
        this.state.openingCash = "0,00";
    }
}


registry.category("actions").add("pos_conventional_opening_popup", OpeningPopup);
