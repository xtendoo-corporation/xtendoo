/** @odoo-module */

import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(Navbar.prototype, {
    /**
     * Opens the cash drawer using the hardware proxy service
     */
    async openCashDrawer() {
        try {
            // Check if printer is available
            if (!this.hardwareProxy.printer) {
                this.notification.add(
                    _t("No printer connected. Connect a receipt printer with cash drawer to use this feature."),
                    { type: "warning" }
                );
                return;
            }
            await this.hardwareProxy.openCashbox("MANUAL_OPEN");
            this.notification.add(_t("Cash drawer opened"), { type: "success" });
        } catch (error) {
            console.error("[POS Open Cash Drawer] Error:", error);
            this.notification.add(_t("Error opening cash drawer"), { type: "danger" });
        }
    },

    /**
     * Check if the cash drawer button should be displayed
     * Always show for non-minimal users - the function handles hardware availability
     * @returns {boolean}
     */
    get showOpenCashDrawerButton() {
        return this.pos.cashier._role !== "minimal";
    },
});

