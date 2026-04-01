/** @odoo-module **/
/**
 * CashDrawerNavbarButton - Botón de apertura del cajón en el Navbar del TPV.
 *
 * Solo se muestra cuando hay una URL configurada en pos.config.
 * Usa la misma lógica de petición que el botón de ControlButtons.
 */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { sendCashDrawerRequest } from "./cash_drawer_utils";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";

export class CashDrawerNavbarButton extends Component {
    static template = "xtendoo_cash_drawer.CashDrawerNavbarButton";
    static props = {};

    setup() {
        this.pos = usePos();
        this.notification = useService("notification");
        this.state = useState({ sending: false });
    }

    get isVisible() {
        return !!this.pos.config.cash_drawer_open_url;
    }

    async onClick() {
        if (this.state.sending) return;
        this.state.sending = true;
        try {
            await sendCashDrawerRequest(
                this.pos.config.cash_drawer_open_url,
                this.pos.config.cash_drawer_api_key
            );
            this.notification.add(_t("Cajón abierto."), { type: "success" });
        } catch (err) {
            this.notification.add(
                _t("Error al abrir el cajón: ") + (err.message || String(err)),
                { type: "danger", sticky: true }
            );
            console.error("[CashDrawer] Error:", err);
        } finally {
            this.state.sending = false;
        }
    }
}

// Registrar el componente en el Navbar del POS
Navbar.components = { ...Navbar.components, CashDrawerNavbarButton };

