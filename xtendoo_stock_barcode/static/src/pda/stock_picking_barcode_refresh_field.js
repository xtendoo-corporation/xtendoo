/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, xml } from "@odoo/owl";

export class StockPickingBarcodeRefreshField extends Component {
    static props = { ...standardFieldProps };
    static supportedTypes = ["char"];
    static template = xml`<div class="d-none"/>`;

    setup() {
        this.barcode = useService("barcode");
        this.orm = useService("orm");
        this.isProcessing = false;
        useBus(this.barcode.bus, "barcode_scanned", this.onBarcodeScanned.bind(this));
    }

    async onBarcodeScanned(event) {
        const { barcode } = event.detail;
        if (!barcode || this.isProcessing || !this.props.record.resId) {
            return;
        }
        this.isProcessing = true;
        try {
            await this.orm.call("stock.picking", "action_scan_barcode", [
                [this.props.record.resId],
                barcode,
            ]);
            await this.props.record.model.root.load();
        } finally {
            this.isProcessing = false;
        }
    }
}

registry.category("fields").add("xtendoo_stock_barcode_scanner", {
    component: StockPickingBarcodeRefreshField,
});
