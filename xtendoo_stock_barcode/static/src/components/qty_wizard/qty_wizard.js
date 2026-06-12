/** @odoo-module **/

import { Component, useState, onRendered } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class QtyWizard extends Component {
    static template = "xtendoo_stock_barcode.QtyWizard";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        confirm: { type: Function },
        close: { type: Function },
    };

    setup() {
        this.state = useState({
            qty: 1,
        });
        onRendered(() => {
            const input = document.querySelector(".o_qty_wizard_input");
            if (input) {
                input.focus();
                input.select();
            }
        });
    }

    _onConfirm() {
        const val = parseFloat(this.state.qty);
        if (!isNaN(val) && val > 0) {
            this.props.confirm(val);
        }
        this.props.close();
    }

    _onCancel() {
        this.props.close();
    }
}

