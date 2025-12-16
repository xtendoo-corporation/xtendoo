/** @odoo-module **/
/**
 * SerialScaleButton - Botón para acceder a la balanza serie en el POS
 */

import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { SerialScalePopup } from "./serial_scale_popup";
import { CONNECTION_STATUS } from "./serial_scale_service";

export class SerialScaleButton extends Component {
    static template = "xtendoo_pos_serial_scale.SerialScaleButton";
    static props = {};

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.serialScale = useService("serial_scale");

        this.state = useState({
            refreshKey: 0,
        });

        onWillStart(() => {
            // Cargar configuración
            if (this.pos.config) {
                this.serialScale.loadConfig(this.pos.config);
            }
        });

        // Actualizar el icono de estado periódicamente
        this.intervalId = setInterval(() => {
            this.state.refreshKey++;
        }, 1000);

        onWillUnmount(() => {
            if (this.intervalId) {
                clearInterval(this.intervalId);
            }
        });
    }

    get isEnabled() {
        return this.serialScale.config.enabled;
    }

    get isConnected() {
        return this.serialScale.status === CONNECTION_STATUS.CONNECTED;
    }

    get statusIcon() {
        switch (this.serialScale.status) {
            case CONNECTION_STATUS.CONNECTED:
                return "fa-check-circle text-success";
            case CONNECTION_STATUS.CONNECTING:
                return "fa-spinner fa-spin text-warning";
            case CONNECTION_STATUS.DISCONNECTED:
                return "fa-circle text-secondary";
            case CONNECTION_STATUS.ERROR:
                return "fa-exclamation-circle text-danger";
            case CONNECTION_STATUS.NOT_SUPPORTED:
                return "fa-ban text-danger";
            default:
                return "fa-question-circle text-muted";
        }
    }

    get statusColor() {
        return this.serialScale.getStatusColor();
    }

    get buttonClass() {
        const base = "btn btn-light btn-lg lh-lg serial-scale-button";
        if (this.isConnected) {
            return `${base} border-success`;
        }
        return base;
    }

    onClick() {
        this.dialog.add(SerialScalePopup, {});
    }
}

// Registrar el componente en el Navbar
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
Navbar.components = { ...Navbar.components, SerialScaleButton };
