/**@odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { CustomAlertPopup } from "@pos_buttons/js/custom_alert_popup";
export class CreateButton extends Component {

    static template = "point_of_sale.CreateButton";

    /**
    * Setup function to initialize the component.
    */

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
    }

    /**
    * Click event handler for the create button.
    */

    async onClick() {
        console.log("Custom Alert Popup");
        this.popup.add(CustomAlertPopup, {
            title: _t('Custom Alert'),
            body: _t('Choose the alert type')
        })
    }
}
/**
* Add the OrderlineProductCreateButton component to the control buttons in
  the ProductScreen.
*/
ProductScreen.addControlButton({
    component: CreateButton,
});
