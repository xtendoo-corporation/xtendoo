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

patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.printer = useService("printer");
    },

    /**
     * Opens the cash drawer by printing a dummy receipt.
     * Relying on the printer's hardware configuration for actual opening.
     */
    async openCashDrawer() {
        if (!this.pos.config.cash_drawer_dummy_print) {
            return;
        }

        try {
            // Trigger the dummy print using the standard printer service
            // This is equivalent to any other receipt printing in the POS
            const printResult = await this.printer.print(
                "cash_drawer_settings.CashDrawerReceipt",
                {
                    dummy_text: this.pos.config.cash_drawer_dummy_text || ".",
                },
                {
                    webPrintFallback: this.pos.config.cash_drawer_web_print_fallback,
                }
            );

            if (printResult) {
                this.notification.add(
                    _t("Cash drawer signal sent (via dummy print)."),
                    { type: "success" }
                );
            } else if (this.pos.config.cash_drawer_web_print_fallback) {
                // If using web print, it's successful as long as it opens the browser dialog
                this.notification.add(
                    _t("Printing dummy receipt..."),
                    { type: "info" }
                );
            }
        } catch (err) {
            this.notification.add(
                _t("Could not open cash drawer: ") + (err.message || String(err)),
                { type: "danger", sticky: true }
            );
            console.error("[CashDrawer] Dummy print failed:", err);
        }
    },
});
