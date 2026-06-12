/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart, useState } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class XtendooStockBarcodePickingClientAction extends Component {
    static template = "xtendoo_stock_barcode.PickingClientAction";
    static props = { ...standardActionServiceProps };

    setup() {
        this.actionService = useService("action");
        this.barcodeService = useService("barcode");
        this.notificationService = useService("notification");
        this.orm = useService("orm");
        this.dialogService = useService("dialog");

        this.pickingId = this.props.action.params.picking_id;
        this.locationId = this.props.action.params.location_id;
        this.mode = this.props.action.params.mode || 'standard';

        this.state = useState({
            loading: true,
            updating: false,
            picking: null,
            lastMessage: false,
            lastMessageSuccess: false,
            isWarning: false,
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

            if (navigator.vibrate) {
                if (type === 'error' || type === 'excess') {
                    navigator.vibrate([100, 50, 100]);
                } else {
                    navigator.vibrate(50);
                }
            }
        } catch(e) {}
    }

    async loadData() {
        if (!this.state.picking) {
            this.state.loading = true;
        } else {
            this.state.updating = true;
        }
        try {
            if (this.mode === 'aggregated') {
                this.state.picking = await this.orm.call("stock.picking", "action_xt_get_aggregated_barcode_data", [this.locationId]);
            } else {
                this.state.picking = await this.orm.call("stock.picking", "action_xt_get_barcode_data", [this.pickingId]);
            }
        } catch (error) {
            this.notificationService.add(_t("Error al cargar datos."), { type: "danger" });
        } finally {
            this.state.loading = false;
            this.state.updating = false;
        }
    }

    async onBarcodeScanned(barcode) {
        if (!this.state.picking || this.state.picking.state === 'done') return;

        try {
            let result;
            if (this.mode === 'aggregated') {
                result = await this.orm.call("stock.picking", "action_xt_process_aggregated_barcode_scan", [this.locationId, barcode]);
            } else {
                result = await this.orm.call("stock.picking", "action_xt_process_barcode_scan", [this.pickingId, barcode]);
            }

            if (result.success) {
                this.state.lastMessage = result.message;
                this.state.lastMessageSuccess = true;
                this.state.isWarning = result.excess || false;
                if (result.excess) {
                    this.playSound('excess');
                } else {
                    this.playSound('success');
                }
                await this.loadData(); // Recargar líneas para actualizar la interfaz
            } else if (result.type === 'excess_confirmation') {
                this.playSound('excess');
                this.dialogService.add(ConfirmationDialog, {
                    body: result.message,
                    confirm: async () => {
                        let forceResult;
                        if (this.mode === 'aggregated') {
                            forceResult = await this.orm.call("stock.picking", "action_xt_process_aggregated_barcode_scan", [this.locationId, barcode, true]);
                        } else {
                            forceResult = await this.orm.call("stock.picking", "action_xt_process_barcode_scan", [this.pickingId, barcode, true]);
                        }
                        if (forceResult.success) {
                            this.state.lastMessage = forceResult.message;
                            this.state.lastMessageSuccess = true;
                            this.state.isWarning = true;
                            this.playSound('success');
                            await this.loadData();
                        } else {
                            this.state.lastMessage = forceResult.error || _t("Error al escanear.");
                            this.state.lastMessageSuccess = false;
                            this.state.isWarning = false;
                            this.playSound('error');
                        }
                    },
                    cancel: () => {},
                });
            } else {
                this.state.lastMessage = result.error || _t("Error al escanear.");
                this.state.lastMessageSuccess = false;
                this.state.isWarning = false;
                this.playSound('error');
            }
        } catch (error) {
            this.state.lastMessage = error.message?.data?.message || error.message || _t("Error inesperado al escanear.");
            this.state.lastMessageSuccess = false;
            this.playSound('error');
        }
    }

    async completeLine(line) {
        if (!this.state.picking || this.state.picking.state === 'done') return;

        // Actualización optimista
        const originalQty = line.qty_done;
        line.qty_done = line.qty_demand;

        try {
            let result;
            if (this.mode === 'aggregated') {
                result = await this.orm.call("stock.picking", "action_xt_complete_aggregated_line", [line.move_ids]);
            } else {
                result = await this.orm.call("stock.picking", "action_xt_complete_line", [this.pickingId, line.id]);
            }

            if (result.success) {
                this.state.lastMessage = _t("Línea completada correctamente.");
                this.state.lastMessageSuccess = true;
                this.playSound('success');
                await this.loadData();
            } else {
                line.qty_done = originalQty;
                this.state.lastMessage = result.error || _t("Error al completar la línea.");
                this.state.lastMessageSuccess = false;
                this.playSound('error');
            }
        } catch (error) {
            line.qty_done = originalQty;
            this.state.lastMessage = error.message?.data?.message || error.message || _t("Error inesperado al completar la línea.");
            this.state.lastMessageSuccess = false;
            this.playSound('error');
        }
    }

    async resetLine(line) {
        if (!this.state.picking || this.state.picking.state === 'done') return;

        // Actualización optimista
        const originalQty = line.qty_done;
        line.qty_done = 0;

        try {
            if (this.mode === 'aggregated') {
                await this.orm.call("stock.picking", "action_xt_reset_aggregated_line", [line.move_ids]);
            } else {
                await this.orm.call("stock.picking", "action_xt_reset_line", [this.pickingId, line.id]);
            }
            await this.loadData();
        } catch (error) {
            line.qty_done = originalQty;
        }
    }

    async adjustQty(line, qty) {
        if (!this.state.picking || this.state.picking.state === 'done') return;

        // Actualización optimista
        const originalQty = line.qty_done;
        line.qty_done = Math.max(0, line.qty_done + qty);

        try {
            let result;
            if (this.mode === 'aggregated') {
                result = await this.orm.call("stock.picking", "action_xt_add_aggregated_qty", [line.move_ids, qty]);
            } else {
                result = await this.orm.call("stock.picking", "action_xt_adjust_qty", [this.pickingId, line.id, qty]);
            }

            if (result && result.success) {
                this.state.lastMessage = result.message || "";
                this.state.lastMessageSuccess = true;
                this.state.isWarning = result.excess || false;
                if (result.excess) {
                    this.playSound('excess');
                } else {
                    this.playSound('success');
                }
                await this.loadData();
            } else if (result && result.type === 'excess_confirmation') {
                line.qty_done = originalQty; // Revertir para preguntar
                this.playSound('excess');
                this.dialogService.add(ConfirmationDialog, {
                    body: result.message || result.error,
                    confirm: async () => {
                        let forceResult;
                        if (this.mode === 'aggregated') {
                            forceResult = await this.orm.call("stock.picking", "action_xt_add_aggregated_qty", [line.move_ids, qty, true]);
                        } else {
                            forceResult = await this.orm.call("stock.picking", "action_xt_adjust_qty", [this.pickingId, line.id, qty, true]);
                        }
                        if (forceResult && forceResult.success) {
                            this.state.lastMessage = forceResult.message || "";
                            this.state.lastMessageSuccess = true;
                            this.state.isWarning = true;
                            this.playSound('success');
                            await this.loadData();
                        }
                    },
                    cancel: () => {},
                });
            } else {
                line.qty_done = originalQty;
                if (result && result.error) {
                    this.notificationService.add(result.error, { type: "danger" });
                }
            }
        } catch (error) {
            line.qty_done = originalQty;
        }
    }

    async validatePicking() {
        try {
            let result;
            if (this.mode === 'aggregated') {
                result = await this.orm.call("stock.picking", "action_xt_validate_aggregated_pickings", [this.locationId]);
            } else {
                result = await this.orm.call("stock.picking", "button_validate", [[this.pickingId]]);
            }

            if (result && result.action) {
                return this.actionService.doAction(result.action);
            }
            if (result && typeof result === 'object' && result.type) {
                return this.actionService.doAction(result);
            }

            // Si llegamos aquí sin redirección, es que se ha validado (éxito manual o sin wizard)
            this.state.lastMessage = _t("Operación validada correctamente. Pulsa salir.");
            this.state.lastMessageSuccess = true;
            this.playSound('success');

            if (result && result.success) {
                this.notificationService.add(result.message || _t("Operación validada correctamente."), { type: "success" });
                if (result.finished) {
                    // Esperar un poco para que el usuario vea el mensaje antes de salir si es automático
                    setTimeout(() => this.exitAction(), 2000);
                } else {
                    await this.loadData();
                }
            } else if (result && result.error) {
                this.notificationService.add(result.error, { type: "danger" });
                this.state.lastMessage = result.error;
                this.state.lastMessageSuccess = false;
                this.playSound('error');
            } else {
                // Caso por defecto: se ha validado pero no hay respuesta estructurada (ej. button_validate directo)
                await this.loadData();
            }
        } catch (error) {
            const msg = error.message?.data?.message || error.message || _t("Error al validar el picking.");
            this.notificationService.add(msg, { type: "danger" });
            this.state.lastMessage = msg;
            this.state.lastMessageSuccess = false;
            this.playSound('error');
        }
    }

    exitAction() {
        if (this.mode === 'aggregated') {
            this.actionService.doAction("xtendoo_stock_barcode.action_xtendoo_stock_barcode_main_menu", { clear_breadcrumbs: true });
        } else {
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
}

registry.category("actions").add("xtendoo_stock_barcode_client_action", XtendooStockBarcodePickingClientAction);
