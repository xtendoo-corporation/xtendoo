/** @odoo-module **/
/**
 * Tour JS to verify the 'Open Cash Drawer' integration in Odoo 19 POS.
 */

import { registry } from "@web/core/registry";

/**
 * Tour: Verify that the button appears in the burger menu when enabled.
 */
registry.category("web_tour.tours").add("cash_drawer_dummy_print_visible", {
    url: "/pos/ui",
    steps: () => [
        {
            content: "Open POS burger menu",
            trigger: ".pos-topheader button .fa-bars",
            run: "click",
        },
        {
            content: "Verify that 'Open Cash Drawer' button is present",
            trigger: ".pos-burger-menu-items .dropdown-item:contains('Open Cash Drawer')",
            run: () => {
                console.log("[CashDrawerTour] ✅ Open Cash Drawer button found");
            },
        },
    ],
});

/**
 * Tour: Verify that the button is hidden when disabled.
 */
registry.category("web_tour.tours").add("cash_drawer_dummy_print_hidden", {
    url: "/pos/ui",
    steps: () => [
        {
            content: "Open POS burger menu",
            trigger: ".pos-topheader button .fa-bars",
            run: "click",
        },
        {
            content: "Verify that the button is hidden",
            trigger: ".pos-burger-menu-items",
            run: () => {
                const items = document.querySelectorAll(".pos-burger-menu-items .dropdown-item");
                const found = Array.from(items).some((el) => el.textContent.includes("Open Cash Drawer"));
                if (found) {
                    throw new Error("The button should be hidden when cash_drawer_dummy_print is false");
                }
                console.log("[CashDrawerTour] ✅ Button correctly hidden");
            },
        },
    ],
});
