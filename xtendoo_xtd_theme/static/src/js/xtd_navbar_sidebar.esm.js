/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { AppsMenu } from "@web_responsive/components/apps_menu/apps_menu.esm";
import { patch } from "@web/core/utils/patch";
import { useBus, useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { onMounted, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";

const XTD_DASHBOARD_MENU_XMLID = "xtendoo_xtd_theme.menu_xtd_dashboard";
const XTD_SIDEBAR_HIDDEN_CLASS = "xtd-sidebar-hidden";
const XTD_SETTINGS_MENU_XMLID = "base.menu_administration";

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.xtdState = useState({
            // Colapsado (solo iconos) por defecto; se expande al pasar el
            // cursor por encima (ver xtd_sidebar_toggle.scss, :hover sobre
            // body.xtd-sidebar-hidden .xtd-sidebar-panel). Que colapse no
            // significa que desaparezca: eso lo garantiza _closeAppMenuSidebar
            // más abajo, que es un estado del core totalmente independiente.
            isSidebarVisible: false,
            // En Ajustes el menú arranca contraído del todo; esto recuerda si
            // el usuario lo ha sacado a mano durante esa visita.
            settingsExpanded: false,
            // Preferencia guardada (reactiva, para que la flecha repinte).
            userSidebarOff: user.settings?.xtd_show_sidebar === false,
        });
        this.xtdCommand = useService("command");
        this.xtdNavbarSearchRef = useRef("xtdNavbarSearch");
        this.xtdSidebarState = useState({
            isReordering: false,
            orderVersion: 0,
        });

        // Forzamos el estado interno para que el sidebar esté "abierto" en el DOM
        // y configurado para mostrar todas las aplicaciones.
        this.state.isAppMenuSidebarOpened = !this.ui.isSmall;
        this.state.isAllAppsMenuOpened = true;
        onMounted(() => {
            // Colapsado por defecto tanto en escritorio (icon-rail, se
            // expande con :hover) como en móvil (overlay cerrado).
            document.body.classList.add(XTD_SIDEBAR_HIDDEN_CLASS);

            // Odoo no define --o-navbar-height en esta versión. El sidebar
            // (xtd_sidebar_toggle.scss) la usa para saber dónde empezar
            // debajo de la navbar; sin ella caía siempre a un valor de
            // reserva que no coincidía con la altura real (dejaba un hueco
            // visible, sobre todo en apps con doble fila de menú tipo
            // Ventas). La medimos de verdad y la mantenemos al día con un
            // ResizeObserver, para que valga tanto con navbar de una fila
            // como de dos.
            const navbarEl = document.querySelector(".o_main_navbar");
            if (navbarEl) {
                this._xtdNavbarResizeObserver = new ResizeObserver(() => {
                    document.documentElement.style.setProperty(
                        "--o-navbar-height",
                        `${navbarEl.offsetHeight}px`
                    );
                });
                this._xtdNavbarResizeObserver.observe(navbarEl);
            }
        });

        useEffect(
            (isOff) => {
                document.body.classList.toggle("xtd-no-sidebar", isOff);
            },
            () => [this.isXtdSidebarOff]
        );
        useEffect(
            (inSettings) => {
                if (!inSettings) {
                    this.xtdState.settingsExpanded = false;
                }
            },
            () => [this.isXtdInSettings]
        );

        onWillUnmount(() => {
            document.body.classList.remove("xtd-no-sidebar");
            this._xtdNavbarResizeObserver?.disconnect();
        });

        useBus(this.env.bus, "XTD_SIDEBAR:TOGGLE", () => {
            this.toggleXtdSidebar();
        });
    },

    get isXtdInSettings() {
        return this.currentApp?.xmlid === XTD_SETTINGS_MENU_XMLID;
    },

    // Menú lateral contraído del todo: en Ajustes siempre (salvo que el
    // usuario lo saque a mano) y en el resto según su preferencia. En móvil
    // nunca, porque es la única forma de navegar entre apps.
    get isXtdSidebarOff() {
        if (this.ui.isSmall) {
            return false;
        }
        if (this.isXtdInSettings) {
            return !this.xtdState.settingsExpanded;
        }
        return this.xtdState.userSidebarOff;
    },

    async toggleXtdSidebarOff() {
        if (this.isXtdInSettings) {
            this.xtdState.settingsExpanded = !this.xtdState.settingsExpanded;
            return;
        }
        this.xtdState.userSidebarOff = !this.xtdState.userSidebarOff;
        await user.setUserSettings("xtd_show_sidebar", !this.xtdState.userSidebarOff);
    },

    // Solo en el dashboard inicial: en el resto de apps la navbar ya muestra
    // sus propios menús de sección.
    get showXtdNavbarSearch() {
        return !this.ui.isSmall && this.currentApp?.xmlid === XTD_DASHBOARD_MENU_XMLID;
    },

    onXtdNavbarSearchInput(ev) {
        const value = ev.target.value;
        if (value) {
            ev.target.value = "";
            this.xtdCommand.openMainPalette({ searchValue: `/${value}` }, null);
        }
    },

    onXtdNavbarSearchClick() {
        this.xtdCommand.openMainPalette({ searchValue: "/" }, null);
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
        // El core cierra isAppMenuSidebarOpened al seleccionar cualquier menú
        // (_onMenuClicked) o desde nuestro propio template al cambiar de app.
        // En escritorio el sidebar es persistente y nunca debe cerrarse: lo
        // reabrimos inmediatamente pase lo que pase por aquí.
        if (!this.ui.isSmall) {
            this.state.isAppMenuSidebarOpened = true;
        }
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
        const hiddenIds = new Set(this._getStoredSidebarHiddenApps());
        const sidebarApps = apps.filter((app) => (
            app.xmlid !== XTD_DASHBOARD_MENU_XMLID
            && (this.xtdSidebarState.isReordering || !hiddenIds.has(app.id))
        ));
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

    isXtdSidebarAppHidden(app) {
        return this._getStoredSidebarHiddenApps().includes(app.id);
    },

    async toggleXtdSidebarAppHidden(app) {
        const hiddenIds = this._getStoredSidebarHiddenApps();
        await user.setUserSettings(
            "xtd_sidebar_hidden_apps",
            hiddenIds.includes(app.id)
                ? hiddenIds.filter((id) => id !== app.id)
                : [...hiddenIds, app.id]
        );
        this.xtdSidebarState.orderVersion += 1;
    },

    _getStoredSidebarHiddenApps() {
        return Array.isArray(user.settings?.xtd_sidebar_hidden_apps)
            ? user.settings.xtd_sidebar_hidden_apps
            : [];
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
