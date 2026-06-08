import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { ManualBarcodeScanner } from "@barcodes/components/manual_barcode";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onWillStart, useState } from "@odoo/owl";

export class XtendooStockBarcodeMainMenu extends Component {
    static template = "xtendoo_stock_barcode.MainMenu";
    static props = { ...standardActionServiceProps };

    setup() {
        this.actionService = useService("action");
        this.barcodeService = useService("barcode");
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            locationsEnabled: false,
            packagesEnabled: false,
            trackingEnabled: false,
            lastBarcode: false,
            lastMessage: false,
        });

        useBus(this.barcodeService.bus, "barcode_scanned", (ev) =>
            this.onBarcodeScanned(ev.detail.barcode)
        );

        onWillStart(async () => {
            const data = await this.orm.call("stock.picking", "action_xt_barcode_get_main_menu_data", []);
            this.state.locationsEnabled = !!data.groups.locations;
            this.state.packagesEnabled = !!data.groups.package;
            this.state.trackingEnabled = !!data.groups.tracking;
            this.state.loading = false;
        });
    }

    async openManualBarcodeDialog() {
        this.dialogService.add(ManualBarcodeScanner, {
            facingMode: "environment",
            onResult: (barcode) => this.onBarcodeScanned(barcode),
        });
    }

    async openAction(xmlid) {
        try {
            return await this.actionService.doAction(xmlid);
        } catch {
            this.notificationService.add(
                _t("La opción solicitada no está disponible en esta base de datos."),
                {
                    title: _t("Xtendoo Barcode"),
                    type: "warning",
                }
            );
            return false;
        }
    }

    async openPickingsAction() {
        return this.openAction("xtendoo_stock_barcode.action_xtendoo_stock_barcode_pickings");
    }

    async openIncomingAction() {
        return this.openAction("xtendoo_stock_barcode.action_xtendoo_stock_barcode_incoming");
    }

    async openOutgoingAction() {
        return this.openAction("xtendoo_stock_barcode.action_xtendoo_stock_barcode_outgoing");
    }

    async openInternalAction() {
        return this.openAction("xtendoo_stock_barcode.action_stock_barcode_internal_wizard");
    }



    async onBarcodeScanned(barcode) {
        this.state.lastBarcode = barcode;
        const result = await this.orm.call("stock.picking", "action_xt_barcode_scan_from_main_menu", [barcode]);
        if (result.action) {
            this.state.lastMessage = _t("Código procesado correctamente.");
            return this.actionService.doAction(result.action);
        }
        const warning = result.warning || {};
        this.state.lastMessage = warning.message || warning || _t("No se pudo resolver el código.");
        this.notificationService.add(this.state.lastMessage, {
            title: warning.title || _t("Xtendoo Barcode"),
            type: "danger",
        });
    }

    get helperBullets() {
        const bullets = [
            _t("Escanea un picking para abrirlo directamente."),
            _t("Escanea un tipo de operación para crear una nueva operación."),
            _t("Escanea un producto o su embalaje para localizar stock interno."),
        ];
        if (this.state.locationsEnabled) {
            bullets.push(_t("Escanea una ubicación interna para iniciar un traslado interno."));
        }
        if (this.state.trackingEnabled) {
            bullets.push(_t("Escanea un lote o serie para abrir su ficha."));
        }
        if (this.state.packagesEnabled) {
            bullets.push(_t("Escanea un paquete para abrirlo."));
        }
        return bullets;
    }
}

registry.category("actions").add("xtendoo_stock_barcode_main_menu", XtendooStockBarcodeMainMenu);
