/** @odoo-module **/
/**
 * Cash Drawer - POS 19
 *
 * Adds the 'Open Cash Drawer' button to the POS control panel and implements
 * a four-tier priority cascade to open the drawer WITHOUT printing whenever
 * possible.
 *
 * Priority order (first success wins – no print job is triggered by P1/P2/P3):
 *   P1 – printerDevice.openCashbox()   Direct hardware command via the ePOS SDK.
 *   P2 – server-side ESC/POS via RPC   Odoo sends raw bytes over TCP / CUPS.
 *                                       Requires 'Cash Drawer Printer Address'
 *                                       to be set in POS configuration.
 *   P3 – hardwareProxy.openCashbox()   Odoo IoT Box / hardware proxy service.
 *   P4 – dummy print fallback          Sends a minimal receipt to the printer
 *                                       so the printer itself opens the drawer.
 *                                       Only used when 'cash_drawer_dummy_print'
 *                                       is enabled in the POS configuration.
 */

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { CashDrawerReceipt } from "./cash_drawer_receipt";


patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.printer      = useService("printer");
        this.actionService = useService("action");
        this.notification  = useService("notification");
        this.orm           = useService("orm");
    },

    /**
     * Opens the cash drawer using the best available method.
     *
     * Strategies tried in order (no-print strategies are always preferred):
     *   1. printerDevice.openCashbox()  — direct ePOS command, no print job.
     *   2. Server-side ESC/POS via RPC  — Odoo sends raw bytes to the printer
     *      over TCP or CUPS, no print job. Requires 'cash_drawer_printer_address'
     *      to be configured on the POS.
     *   3. hardwareProxy.openCashbox()  — IoT Box / hardware proxy. Sends the
     *      ESC/POS pulse through the proxy daemon, no print job.
     *   4. Dummy print (last resort)    — prints a minimal invisible receipt so
     *      the printer fires the drawer pulse at the end of the job.
     *      Only attempted when 'cash_drawer_dummy_print' is enabled on the POS.
     */
    async openCashDrawer() {
        console.log("[CashDrawer] Attempting to open drawer...");

        try {
            // ----------------------------------------------------------
            // P1 — Direct openCashbox via ePOS printer device (no print)
            // ----------------------------------------------------------
            const printerDevice = this.printer.device;
            if (printerDevice && typeof printerDevice.openCashbox === "function") {
                console.log("[CashDrawer] P1: printerDevice.openCashbox()");
                await printerDevice.openCashbox();
                this.notification.add(_t("Cash drawer opened."), { type: "success" });
                return;
            }

            // ----------------------------------------------------------
            // P2 — Server-side direct ESC/POS via JSON-RPC (no print)
            //      Odoo backend calls open_cash_drawer() using TCP / CUPS.
            //      Requires 'cash_drawer_printer_address' to be configured.
            // ----------------------------------------------------------
            const config = this.pos.config;
            if (config.cash_drawer_printer_address) {
                console.log("[CashDrawer] P2: server-side ESC/POS via RPC");
                try {
                    await this.orm.call(
                        "pos.config",
                        "open_cash_drawer_direct",
                        [[config.id]],
                    );
                    this.notification.add(_t("Cash drawer opened."), { type: "success" });
                    return;
                } catch (rpcErr) {
                    console.warn("[CashDrawer] P2 failed:", rpcErr);
                    // Continue to P3
                }
            }

            // ----------------------------------------------------------
            // P3 — IoT Box / hardware proxy (no print)
            // ----------------------------------------------------------
            if (
                this.pos.hardwareProxy &&
                typeof this.pos.hardwareProxy.openCashbox === "function"
            ) {
                console.log("[CashDrawer] P3: hardwareProxy.openCashbox()");
                await this.pos.hardwareProxy.openCashbox();
                // Note: hardwareProxy.openCashbox() checks iface_cashdrawer
                // internally and may silently do nothing when the IoT Box is
                // not configured. We show success here anyway; if the drawer
                // did not open, the operator should configure P2 instead.
                this.notification.add(_t("Cash drawer signal sent."), { type: "success" });
                return;
            }

            // ----------------------------------------------------------
            // P4 — Dummy print fallback (sends a minimal receipt to the
            //      printer so the printer opens the drawer at end-of-print)
            //      Only used when explicitly enabled in POS configuration.
            // ----------------------------------------------------------
            if (config.cash_drawer_dummy_print) {
                console.log("[CashDrawer] P4: dummy print fallback");
                await this.printer.print(
                    CashDrawerReceipt,
                    { company: this.pos.company },
                    { webPrintFallback: config.cash_drawer_web_print_fallback },
                );
                this.notification.add(
                    _t("Cash drawer signal sent (via print)."),
                    { type: "success" },
                );
                return;
            }

            // No strategy available
            this.notification.add(
                _t(
                    "Could not open cash drawer: no method available.\n" +
                    "Configure 'Cash Drawer Printer Address' or enable the dummy-print fallback."
                ),
                { type: "warning", sticky: true },
            );

        } catch (err) {
            this.notification.add(
                _t("Could not open cash drawer: ") + (err.message || String(err)),
                { type: "danger", sticky: true },
            );
            console.error("[CashDrawer] Action failed:", err);
        }
    },
});

