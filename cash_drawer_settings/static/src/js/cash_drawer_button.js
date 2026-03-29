/** @odoo-module **/
/**
 * Cash Drawer Dummy Print Strategy - POS 19 Refactor
 * 
 * This patch adds the 'Open Cash Drawer' functionality to the POS Navbar.
 * It uses the 'dummy print' strategy: sending a minimal receipt to the 
 * POS printer to trigger its connected drawer mechanism.
 */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { CashDrawerReceipt } from "./cash_drawer_receipt";


patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.printer = useService("printer");
        this.actionService = useService("action");
        this.notification = useService("notification");
    },

    /**
     * Opens the cash drawer by printing a minimal front-end receipt.
     * Relying on the printer's hardware configuration for actual opening.
     */
    async openCashDrawer() {
        console.log("[CashDrawer] Executing client-side print...");
        
        try {
            await this.printer.print(CashDrawerReceipt, {
                company: this.pos.company,
            });

            console.log("[CashDrawer] Client-side print completed.");

            this.notification.add(
                _t("Cash drawer signal sent."),
                { type: "success" }
            );
        } catch (err) {
            this.notification.add(
                _t("Could not open cash drawer: ") + (err.message || String(err)),
                { type: "danger", sticky: true }
            );
            console.error("[CashDrawer] Print failed:", err);
        }
    },

});

