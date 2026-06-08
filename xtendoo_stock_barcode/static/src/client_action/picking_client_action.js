/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart, useState } from "@odoo/owl";

export class XtendooStockBarcodePickingClientAction extends Component {
    static template = "xtendoo_stock_barcode.PickingClientAction";
    static props = { ...standardActionServiceProps };

    setup() {
        this.actionService = useService("action");
        this.barcodeService = useService("barcode");
        this.notificationService = useService("notification");
        this.orm = useService("orm");

        this.pickingId = this.props.action.params.picking_id;

        this.state = useState({
            loading: true,
            picking: null,
            lastMessage: false,
            lastMessageSuccess: false,
        });

        useBus(this.barcodeService.bus, "barcode_scanned", (ev) =>
            this.onBarcodeScanned(ev.detail.barcode)
        );

        onWillStart(async () => {
            await this.loadData();
        });
    }

    playSound(type) {
        try {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioCtx.createOscillator();
            const gainNode = audioCtx.createGain();
            oscillator.connect(gainNode);
            gainNode.connect(audioCtx.destination);
            
            if (type === 'error' || type === 'excess') {
                oscillator.type = 'square';
                oscillator.frequency.setValueAtTime(400, audioCtx.currentTime);
                oscillator.frequency.exponentialRampToValueAtTime(100, audioCtx.currentTime + 0.3);
                gainNode.gain.setValueAtTime(0.5, audioCtx.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
                oscillator.start();
                oscillator.stop(audioCtx.currentTime + 0.3);
            } else if (type === 'success') {
                oscillator.type = 'sine';
                oscillator.frequency.setValueAtTime(600, audioCtx.currentTime);
                oscillator.frequency.setValueAtTime(800, audioCtx.currentTime + 0.1);
                gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.2);
                oscillator.start();
                oscillator.stop(audioCtx.currentTime + 0.2);
            }
        } catch(e) {}
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.picking = await this.orm.call("stock.picking", "action_xt_get_barcode_data", [this.pickingId]);
        } catch (error) {
            this.notificationService.add(_t("Error al cargar datos del picking."), { type: "danger" });
        }
        this.state.loading = false;
    }

    async onBarcodeScanned(barcode) {
        if (!this.state.picking || this.state.picking.state === 'done') return;
        
        try {
            const result = await this.orm.call("stock.picking", "action_xt_process_barcode_scan", [this.pickingId, barcode]);
            if (result.success) {
                this.state.lastMessage = result.message;
                this.state.lastMessageSuccess = true;
                if (result.excess) {
                    this.playSound('excess');
                } else {
                    this.playSound('success');
                }
                await this.loadData(); // Recargar líneas para actualizar la interfaz
            } else {
                this.state.lastMessage = result.error || _t("Error al escanear.");
                this.state.lastMessageSuccess = false;
                this.playSound('error');
            }
        } catch (error) {
            this.state.lastMessage = error.message?.data?.message || error.message || _t("Error inesperado al escanear.");
            this.state.lastMessageSuccess = false;
            this.playSound('error');
        }
    }

    async completeLine(moveId) {
        if (!this.state.picking || this.state.picking.state === 'done') return;
        
        try {
            const result = await this.orm.call("stock.picking", "action_xt_complete_line", [this.pickingId, moveId]);
            if (result.success) {
                this.state.lastMessage = _t("Línea completada correctamente.");
                this.state.lastMessageSuccess = true;
                this.playSound('success');
                await this.loadData();
            } else {
                this.state.lastMessage = result.error || _t("Error al completar la línea.");
                this.state.lastMessageSuccess = false;
                this.playSound('error');
            }
        } catch (error) {
            this.state.lastMessage = error.message?.data?.message || error.message || _t("Error inesperado al completar la línea.");
            this.state.lastMessageSuccess = false;
            this.playSound('error');
        }
    }

    async validatePicking() {
        try {
            const result = await this.orm.call("stock.picking", "button_validate", [[this.pickingId]]);
            if (result && typeof result === 'object' && result.type) {
                return this.actionService.doAction(result);
            }
            this.notificationService.add(_t("Picking validado correctamente."), { type: "success" });
            this.exitAction();
        } catch (error) {
            this.notificationService.add(error.message?.data?.message || _t("Error al validar el picking."), { type: "danger" });
        }
    }

    exitAction() {
        // Fallback to open the form view directly if going back fails
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "stock.picking",
            res_id: parseInt(this.pickingId),
            views: [[false, "form"]],
            target: "main",
        });
    }
}

registry.category("actions").add("xtendoo_stock_barcode_client_action", XtendooStockBarcodePickingClientAction);
