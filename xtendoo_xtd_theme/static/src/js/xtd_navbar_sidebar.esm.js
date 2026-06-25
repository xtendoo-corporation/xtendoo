/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { AppsMenu } from "@web_responsive/components/apps_menu/apps_menu.esm";
import { patch } from "@web/core/utils/patch";
import { useBus, useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { onMounted, useState } from "@odoo/owl";

const XTD_DASHBOARD_MENU_XMLID = "xtendoo_xtd_theme.menu_xtd_dashboard";
const XTD_SIDEBAR_HIDDEN_CLASS = "xtd-sidebar-hidden";

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.xtdState = useState({
            isSidebarVisible: false,
        });
        this.xtdSidebarState = useState({
            isReordering: false,
            orderVersion: 0,
        });

        // Forzamos el estado interno para que el sidebar esté "abierto" en el DOM
        // y configurado para mostrar todas las aplicaciones.
        this.state.isAppMenuSidebarOpened = !this.ui.isSmall;
        this.state.isAllAppsMenuOpened = true;
        onMounted(() => {
            document.body.classList.add(XTD_SIDEBAR_HIDDEN_CLASS);
        });

        useBus(this.env.bus, "XTD_SIDEBAR:TOGGLE", () => {
            this.toggleXtdSidebar();
        });
    },

    toggleXtdSidebar() {
        this.xtdState.isSidebarVisible = !this.xtdState.isSidebarVisible;
        document.body.classList.toggle(XTD_SIDEBAR_HIDDEN_CLASS, !this.xtdState.isSidebarVisible);
    },

    _openAppMenuSidebar() {
        super._openAppMenuSidebar(...arguments);
        this._syncXtdMobileSidebarVisibility();
    },

    _closeAppMenuSidebar() {
        super._closeAppMenuSidebar(...arguments);
        this._syncXtdMobileSidebarVisibility();
    },

    _syncXtdMobileSidebarVisibility() {
        if (!this.ui.isSmall) {
            return;
        }
        document.body.classList.toggle(
            XTD_SIDEBAR_HIDDEN_CLASS,
            !this.state.isAppMenuSidebarOpened
        );
    },

    onNavBarDropdownItemSelection(menu) {
        if (menu) {
            this.menuService.selectMenu(menu);
        }
    },

    getXtdSidebarApps(apps) {
        const sidebarApps = apps.filter((app) => app.xmlid !== XTD_DASHBOARD_MENU_XMLID);
        const storedOrder = this._getStoredSidebarOrder();
        if (!storedOrder.length) {
            return sidebarApps;
        }
        const orderIndexById = new Map(storedOrder.map((id, index) => [id, index]));
        return [...sidebarApps].sort((appA, appB) => {
            const indexA = orderIndexById.has(appA.id) ? orderIndexById.get(appA.id) : Number.MAX_SAFE_INTEGER;
            const indexB = orderIndexById.has(appB.id) ? orderIndexById.get(appB.id) : Number.MAX_SAFE_INTEGER;
            return indexA - indexB;
        });
    },

    toggleXtdSidebarReorder() {
        this.xtdSidebarState.isReordering = !this.xtdSidebarState.isReordering;
    },

    async moveXtdSidebarApp(app, direction) {
        const apps = this.getXtdSidebarApps(this.menuService.getApps());
        const currentIndex = apps.findIndex((candidate) => candidate.id === app.id);
        const nextIndex = currentIndex + direction;
        if (currentIndex < 0 || nextIndex < 0 || nextIndex >= apps.length) {
            return;
        }
        const orderedApps = [...apps];
        const [movedApp] = orderedApps.splice(currentIndex, 1);
        orderedApps.splice(nextIndex, 0, movedApp);
        await user.setUserSettings(
            "xtd_sidebar_app_order",
            orderedApps.map((orderedApp) => orderedApp.id)
        );
        this.xtdSidebarState.orderVersion += 1;
    },

    _getStoredSidebarOrder() {
        return Array.isArray(user.settings?.xtd_sidebar_app_order)
            ? user.settings.xtd_sidebar_app_order
            : [];
    }
});

patch(AppsMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.ui = useState(useService("ui"));
    },

    toggleXtdSidebar() {
        this.env.bus.trigger("XTD_SIDEBAR:TOGGLE");
    },

    onXtdAppsButtonClick() {
        if (this.ui.isSmall) {
            this.env.bus.trigger("APP_MENU:TOGGLE_SIDEBAR");
            return;
        }
        this.goToXtdDashboard();
    },

    async goToXtdDashboard() {
        const apps = this.menuService.getApps();
        const dashboardMenu = apps.find((app) => app.xmlid === XTD_DASHBOARD_MENU_XMLID)
            || apps.find((app) => app.name === "Inicio");
        if (dashboardMenu) {
            await this.menuService.selectMenu(dashboardMenu);
        }
    }
});
