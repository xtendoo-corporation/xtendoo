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
        this.actionService = useService("action");
        this.notification = useService("notification");
    },

    /**
     * Opens the cash drawer by printing a traditional Odoo report.
     * Relying on the printer's hardware configuration for actual opening.
     */
    async openCashDrawer() {
        console.log("[CashDrawer] Executing...");
        
        try {
            const reportAction = "cash_drawer_settings.action_report_cash_drawer_receipt";
            const configId = this.pos.config.id;
            
            console.log("[CashDrawer] Triggering backend report [action_report_cash_drawer_receipt] for ID:", configId);

            // Trigger the traditional backend report
            await this.actionService.doAction({
                type: "ir.actions.report",
                report_name: "cash_drawer_settings.report_cash_drawer_receipt",
                report_type: "qweb-pdf",
                context: {
                    active_ids: [configId],
                    active_id: configId,
                },
            });

            console.log("[CashDrawer] Backend call completed.");

            this.notification.add(
                _t("Cash drawer signal sent."),
                { type: "success" }
            );
        } catch (err) {

            this.notification.add(
                _t("Could not open cash drawer: ") + (err.message || String(err)),
                { type: "danger", sticky: true }
            );
            console.error("[CashDrawer] Report trigger failed:", err);
        }
    },

});

