/** @odoo-module **/
/**
 * SerialScalePopup - Popup para gestionar la balanza serie
 *
 * Este componente OWL proporciona una interfaz para:
 * - Conectar/desconectar la balanza
 * - Ver el peso actual y la línea raw
 * - Aplicar el peso al producto actual
 */

import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { CONNECTION_STATUS } from "./serial_scale_service";

export class SerialScalePopup extends Component {
    static template = "xtendoo_pos_serial_scale.SerialScalePopup";
    static components = { Dialog };
    static props = {
        close: Function,
        getPayload: { type: Function, optional: true },
        applyToProduct: { type: Boolean, optional: true },
    };
    static defaultProps = {
        applyToProduct: false,
    };

    setup() {
        this.pos = usePos();
        this.serialScale = useService("serial_scale");
        this.notification = useService("notification");

        this.state = useState({
            refreshKey: 0,
        });

        onWillStart(() => {
            // Cargar configuración del POS si no está cargada
            if (this.pos.config) {
                this.serialScale.loadConfig(this.pos.config);
            }
        });

        // Actualizar UI periódicamente mientras el popup esté abierto
        this.intervalId = setInterval(() => {
            this.state.refreshKey++;
        }, 500);

        onWillUnmount(() => {
            if (this.intervalId) {
                clearInterval(this.intervalId);
            }
        });
    }

    get isSupported() {
        return this.serialScale.isSupported;
    }

    get isConnected() {
        return this.serialScale.status === CONNECTION_STATUS.CONNECTED;
    }

    get isConnecting() {
        return this.serialScale.status === CONNECTION_STATUS.CONNECTING;
    }

    get status() {
        return this.serialScale.getStatusText();
    }

    get statusColor() {
        return this.serialScale.getStatusColor();
    }

    get lastWeight() {
        return this.serialScale.lastWeight;
    }

    get lastRawLine() {
        return this.serialScale.lastRawLine || "-";
    }

    get errorMessage() {
        return this.serialScale.errorMessage;
    }

    get portHint() {
        return this.serialScale.config.portHint;
    }

    get canApply() {
        return this.props.applyToProduct && this.isConnected && this.lastWeight > 0;
    }

    async onConnect() {
        await this.serialScale.connect();
    }

    async onDisconnect() {
        await this.serialScale.disconnect();
    }

    onApply() {
        if (this.canApply && this.props.getPayload) {
            this.props.getPayload(this.lastWeight);
            this.props.close();
        }
    }

    onClose() {
        this.props.close();
    }

    formatWeight(weight) {
        return weight.toFixed(3) + " kg";
    }
}

