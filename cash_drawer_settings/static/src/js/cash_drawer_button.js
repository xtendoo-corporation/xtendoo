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
        console.log("[CashDrawer] Attempting to open drawer...");
        
        try {
            const printerDevice = this.printer.device;
            
            // Priority 1: Direct openCashbox command on the printer device
            // This bypasses Odoo's standard config checks and avoids paper feed/cuts
            if (printerDevice && typeof printerDevice.openCashbox === "function") {
                console.log("[CashDrawer] Triggering direct openCashbox command...");
                await printerDevice.openCashbox();
                
                this.notification.add(_t("Cash drawer signal sent."), {
                    type: "success",
                });
                return;
            }

            // Priority 2: Use hardware_proxy service's openCashbox (standard way)
            if (this.pos.hardwareProxy && typeof this.pos.hardwareProxy.openCashbox === "function") {
                 console.log("[CashDrawer] Triggering via hardwareProxy...");
                 await this.pos.hardwareProxy.openCashbox();
                 // Note: hardwareProxy.openCashbox checks iface_cashdrawer config internally
                 // If it does nothing, we continue to fallback strategy
            }

            // Priority 3: Minimal receipt print (Fallback for Web Print or non-standard drivers)
            console.log("[CashDrawer] Falling back to minimal print strategy...");
            await this.printer.print(
                CashDrawerReceipt, 
                { company: this.pos.company },
                { webPrintFallback: true }
            );

            this.notification.add(
                _t("Cash drawer signal sent."),
                { type: "success" }
            );
        } catch (err) {
            this.notification.add(
                _t("Could not open cash drawer: ") + (err.message || String(err)),
                { type: "danger", sticky: true }
            );
            console.error("[CashDrawer] Action failed:", err);
        }
    },

});
