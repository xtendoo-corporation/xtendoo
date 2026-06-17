/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { AppsMenu } from "@web_responsive/components/apps_menu/apps_menu.esm";
import { patch } from "@web/core/utils/patch";
import { useBus } from "@web/core/utils/hooks";
import { useState, onWillStart } from "@odoo/owl";

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.xtdState = useState({
            isSidebarVisible: true,
        });

        // Forzamos el estado interno para que el sidebar esté "abierto" en el DOM
        // y configurado para mostrar todas las aplicaciones.
        this.state.isAppMenuSidebarOpened = true;
        this.state.isAllAppsMenuOpened = true;

        useBus(this.env.bus, "XTD_SIDEBAR:TOGGLE", () => {
            this.toggleXtdSidebar();
        });
    },

    toggleXtdSidebar() {
        this.xtdState.isSidebarVisible = !this.xtdState.isSidebarVisible;
        document.body.classList.toggle("xtd-sidebar-hidden", !this.xtdState.isSidebarVisible);
    },

    onNavBarDropdownItemSelection(menu) {
        if (menu) {
            this.menuService.selectMenu(menu);
        }
    }
});

patch(AppsMenu.prototype, {
    toggleXtdSidebar() {
        this.env.bus.trigger("XTD_SIDEBAR:TOGGLE");
    }
});

