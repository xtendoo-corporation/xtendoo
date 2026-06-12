/** @odoo-module **/

import { Component, useState, onRendered } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class ProductDetailView extends Component {
    static template = "xtendoo_stock_barcode.ProductDetailView";
    static props = {
        line: { type: Object },
        onConfirm: { type: Function },
        onClose: { type: Function },
    };

    setup() {
        this.state = useState({
            input_qty: this.props.line.qty_done || 0,
        });

        onRendered(() => {
            const input = document.querySelector(".o_product_detail_input");
            if (input) {
                input.focus();
                input.select(); // Seleccionar texto para facilitar sobreescritura
            }
        });

        // Asegurar el binding de los métodos
        this._onConfirm = this._onConfirm.bind(this);
        this._onClose = this._onClose.bind(this);
        this._addQty = this._addQty.bind(this);
        this._setQty = this._setQty.bind(this);
    }

    _onConfirm() {
        const val = parseFloat(this.state.input_qty);
        // Usar props.line.qty_done para calcular la diferencia correctamente
        this.props.onConfirm(isNaN(val) ? this.props.line.qty_done : val);
    }

    _onClose() {
        this.props.onClose();
    }

    _addQty(val) {
        const current = parseFloat(this.state.input_qty) || 0;
        this.state.input_qty = Math.max(0, current + val);
    }

    _setQty(val) {
        this.state.input_qty = Math.max(0, val);
    }
}
