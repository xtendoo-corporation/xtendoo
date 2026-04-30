/**
 * xtd_section_sidebar.esm.js
 *
 * Sidebar lateral persistente de secciones del módulo activo.
 * Se registra como main_component para renderizarse en el WebClient.
 * Sigue el patrón estándar de Odoo: menuService + main_components registry.
 */

import { Component, onMounted, onPatched, onWillUnmount, useState } from "@odoo/owl";
import { useBus, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const SIDEBAR_BODY_CLASS = "xtd-has-sidebar";

class XtdSectionSidebar extends Component {
    static template = "xtendoo_xtd_theme.SectionSidebar";
    static props = {};

    setup() {
        this.menuService = useService("menu");
        this.state = useState({
            currentApp: null,
            sections: [],
            selectedMenuId: null,
        });

        // Carga inicial: la app puede estar ya seleccionada al montar
        this._refresh();

        // Actualizar cuando cambia la app activa
        useBus(this.env.bus, "MENUS:APP-CHANGED", () => this._refresh());

        // Sincronizar clase CSS en el body al montar, actualizar y desmontar
        onMounted(() => this._syncBodyClass());
        onPatched(() => this._syncBodyClass());
        onWillUnmount(() => document.body.classList.remove(SIDEBAR_BODY_CLASS));
    }

    /** Lee la app y sus secciones desde el servicio de menú. */
    _refresh() {
        const app = this.menuService.getCurrentApp();
        this.state.currentApp = app || null;
        this.state.sections = app
            ? this.menuService.getMenuAsTree(app.id).childrenTree
            : [];
        if (!app) {
            this.state.selectedMenuId = null;
        }
    }

    /**
     * Añade/elimina la clase xtd-has-sidebar del body para que el CSS
     * pueda aplicar el offset al contenido principal.
     */
    _syncBodyClass() {
        const visible = !!(this.state.currentApp && this.state.sections.length);
        document.body.classList.toggle(SIDEBAR_BODY_CLASS, visible);
    }

    /**
     * Navega al menú seleccionado y actualiza el estado activo local.
     * Los menús sin actionID ni actionPath son solo grupos y no son navegables.
     */
    async selectMenu(menu) {
        if (!menu.actionID && !menu.actionPath) {
            return;
        }
        this.state.selectedMenuId = menu.id;
        await this.menuService.selectMenu(menu);
    }

    /** Devuelve el href de un ítem de menú siguiendo el patrón de Odoo. */
    getHref(menu) {
        const path = menu.actionPath || (menu.actionID ? `action-${menu.actionID}` : null);
        return path ? `/odoo/${path}` : "#";
    }

    /** Comprueba si un ítem de menú es el actualmente seleccionado. */
    isActive(menu) {
        return this.state.selectedMenuId === menu.id;
    }
}

registry.category("main_components").add("xtd_section_sidebar", {
    Component: XtdSectionSidebar,
});

