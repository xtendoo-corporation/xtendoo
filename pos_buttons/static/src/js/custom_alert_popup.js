/** @odoo-module */
import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

/**
 * CustomAlertPopup component for displaying custom messages as an alert popup.
 * Inherits from AbstractAwaitablePopup.
 */
export class CustomAlertPopup extends AbstractAwaitablePopup {

    static template = "pos_buttons.CustomAlertPopup";

    static props = {
        title: { type: String, optional: true, default: _t("Error") },
        body: { type: String, optional: true, default: '' },
        confirmText: { type: String, optional: true, default: _t("Ok") },
        zIndex: { type: Number, optional: true, default: 1000 },
        cancelKey: { type: String, optional: true },
        confirmKey: { type: String, optional: true },
        id: { type: Number, optional: true, },
        resolve: { type: Function, optional: true },
        close: { type: Function, optional: true },
    };

    closePopup() {
        if (this.props.close) {
            this.props.close();
        } else {
            console.error("Close method is not defined");
        }
    }

     confirm() {
       if (this.props.resolve) {
           this.props.resolve();
       }
       this.closePopup();
    }

    static defaultProps = {
        confirmText: _t("Ok"),
        title: _t("Error"),
        body: '',
        zIndex: 1000,
    };

    setup() {
        super.setup();
        console.log("Custom Alert Setup");
        console.log("Props recibidos:", this.props);
    }
    onMounted() {
        console.log("Custom Alert Mounted");
    }

}
