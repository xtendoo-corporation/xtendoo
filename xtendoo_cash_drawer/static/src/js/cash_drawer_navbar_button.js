/** @odoo-module **/
/**
 * CashDrawerNavbarButton - Botón de apertura del cajón en el Navbar del TPV.
 *
 * Solo se muestra cuando el bridge del cajón está habilitado y configurado.
 * Reutiliza la acción cliente devuelta por pos.config.action_test_cash_drawer().
 */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { checkCashDrawerHealth, sendCashDrawerRequest } from "./cash_drawer_utils";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";

export class CashDrawerNavbarButton extends Component {
    static template = "xtendoo_cash_drawer.CashDrawerNavbarButton";
    static props = {};

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({ sending: false, bridgeAvailable: null });
    }

    /**
     * Controla la visibilidad del botón.
     * Compatible con nueva arquitectura (cash_drawer_use_bridge + cash_drawer_bridge_url)
     * y con el campo legacy cash_drawer_open_url.
     */
    get isVisible() {
        const cfg = this.pos.config;
        return !!(cfg.cash_drawer_use_bridge && cfg.cash_drawer_bridge_url) ||
               !!(cfg.cash_drawer_open_url);
    }

    /**
     * Devuelve el ID real de pos.config disponible en la sesión POS.
     *
     * @returns {number|null}
     */
    get cashDrawerConfigId() {
        const configId = this.pos.config?.id;
        if (typeof configId === "number") {
            return configId;
        }
        const sessionConfigId = this.pos.pos_session?.config_id;
        if (Array.isArray(sessionConfigId)) {
            return sessionConfigId[0] || null;
        }
        return sessionConfigId || null;
    }

    /**
     * Abre el cajón extrayendo la configuración fresca y enviando la petición.
     * Muestra notificación de éxito o error.
     */
    async onClick() {
        if (this.state.sending) return;
        this.state.sending = true;
        try {
            const configId = this.cashDrawerConfigId;
            if (configId) {
                const action = await this.orm.call(
                    "pos.config",
                    "action_test_cash_drawer",
                    [[configId]]
                );
                if (action) {
                    await this.action.doAction(action);
                }
            }
        } catch (err) {
            this.notification.add(
                _t("Error al intentar abrir el cajón: ") + (err.message || String(err)),
                { type: "danger" }
            );
            console.error("[CashDrawer] Error:", err);
        } finally {
            this.state.sending = false;
        }
    }

    /**
     * Comprueba disponibilidad del bridge al hacer clic largo / desde diagnóstico.
     * No interrumpe el flujo principal.
     */
    async onCheckHealth() {
        const result = await checkCashDrawerHealth(this.pos.config);
        this.state.bridgeAvailable = result.available;
        if (result.available) {
            this.notification.add(
                _t("Bridge del cajón disponible: ") + result.detail,
                { type: "info" }
            );
        } else {
            this.notification.add(
                _t("Bridge del cajón no disponible: ") + result.detail,
                { type: "warning", sticky: true }
            );
        }
    }
}

// Registrar el componente en el Navbar del POS
Navbar.components = { ...Navbar.components, CashDrawerNavbarButton };
