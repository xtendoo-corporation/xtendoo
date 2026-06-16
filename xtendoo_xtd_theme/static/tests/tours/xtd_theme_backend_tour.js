import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("xtd_theme_backend_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: ".o_main_navbar .o_menu_sections",
        },
        {
            trigger: ".o_grid_apps_menu__button",
            run: "click",
        },
        {
            trigger: ".app-menu-container .o-app-menu-list",
        },
        {
            trigger: "body",
            run() {
                if (document.querySelector(".xtd-section-sidebar")) {
                    throw new Error("El theme no debe renderizar un sidebar lateral persistente.");
                }
                if (document.body.classList.contains("xtd-has-sidebar")) {
                    throw new Error("El body no debe desplazarse por un sidebar lateral Xtd.");
                }
            },
        },
        {
            trigger: '.app-menu-container a[data-menu-xmlid="base.menu_administration"]',
            run: "click",
        },
        {
            trigger: ".o_base_settings_view .settings_tab .tab.selected",
        },
        {
            trigger: "body",
            run() {
                const activeTab = document.querySelector(
                    ".o_base_settings_view .settings_tab .tab.selected, " +
                    ".o_base_settings_view .settings_tab .tab.current, " +
                    ".o_base_settings_view .settings_tab .tab.text-bg-primary"
                );
                if (!activeTab) {
                    throw new Error("No se ha encontrado la pestaña activa de Ajustes.");
                }
                const activeTabStyle = window.getComputedStyle(activeTab);
                if (activeTabStyle.backgroundColor === "rgb(74, 8, 35)") {
                    throw new Error("La pestaña activa de Ajustes no debe usar fondo morado.");
                }
                if (activeTabStyle.color !== "rgb(74, 8, 35)") {
                    throw new Error("La pestaña activa de Ajustes debe usar texto borgoña Xtd.");
                }
                if (!activeTabStyle.boxShadow.includes("255, 79, 0")) {
                    throw new Error("La pestaña activa de Ajustes debe resaltar con el acento naranja Xtd.");
                }

                const menuBrand = document.querySelector(".o_main_navbar .o_menu_brand");
                if (!menuBrand) {
                    throw new Error("No se ha encontrado el título de la app en el navbar.");
                }
                const menuBrandStyle = window.getComputedStyle(menuBrand);
                if (menuBrandStyle.textDecorationLine !== "none") {
                    throw new Error("El título de la app no debe mostrarse subrayado en el navbar.");
                }
                if (parseFloat(menuBrandStyle.fontSize) > 16.5) {
                    throw new Error("El título de la app del navbar no debe quedar sobredimensionado.");
                }
                if (parseFloat(menuBrandStyle.height) > 32.5) {
                    throw new Error("El título de la app del navbar debe conservar una altura compacta.");
                }

                const searchIcon = document.querySelector(".o_searchview_icon");
                if (!searchIcon) {
                    throw new Error("No se ha encontrado un icono visible para validar el color global.");
                }
                const searchIconStyle = window.getComputedStyle(searchIcon);
                if (searchIconStyle.color !== "rgb(21, 21, 21)") {
                    throw new Error("Los iconos del backend deben mostrarse en negro en el tema claro.");
                }

                const systrayEntry = document.querySelector(
                    ".o_main_navbar .o_menu_systray .dropdown-toggle, " +
                    ".o_main_navbar .o_menu_systray .btn, " +
                    ".o_main_navbar .o_menu_systray > li > a, " +
                    ".o_main_navbar .o_menu_systray > li > button"
                );
                if (systrayEntry) {
                    const systrayEntryStyle = window.getComputedStyle(systrayEntry);
                    if (parseFloat(systrayEntryStyle.height) > 32.5) {
                        throw new Error(
                            "Las entradas del systray deben conservar una altura compacta para no invadir el separador inferior del navbar."
                        );
                    }
                }
            },
        },
        {
            trigger:
                ".o_main_navbar .o_menu_sections .dropdown-toggle:not(.o-dropdown-toggle-custo), " +
                ".o_main_navbar .o_menu_sections .o_nav_entry",
            run: "click",
        },
        {
            trigger: "body",
            run() {

                const activeNavbarEntry = document.querySelector(
                    ".o_main_navbar .o_menu_sections .dropdown.show > .dropdown-toggle:not(.o-dropdown-toggle-custo), " +
                    ".o_main_navbar .o_menu_sections .dropdown-toggle[aria-expanded='true']:not(.o-dropdown-toggle-custo), " +
                    ".o_main_navbar .o_menu_sections .o_nav_entry.active, " +
                    ".o_main_navbar .o_menu_sections .o_nav_entry[aria-expanded='true']"
                );
                const navbarEntry =
                    activeNavbarEntry ||
                    document.querySelector(
                        ".o_main_navbar .o_menu_sections .dropdown-toggle:not(.o-dropdown-toggle-custo), " +
                        ".o_main_navbar .o_menu_sections .o_nav_entry"
                    );
                if (!navbarEntry) {
                    throw new Error("No se ha encontrado ninguna entrada visible del menú superior.");
                }
                const navbarEntryStyle = window.getComputedStyle(navbarEntry);
                if (activeNavbarEntry && navbarEntryStyle.backgroundColor === "rgb(74, 8, 35)") {
                    throw new Error("El menú superior no debe mostrar el estado activo con bloque morado.");
                }
                if (parseFloat(navbarEntryStyle.height) > 40.5) {
                    throw new Error("La opción activa del menú superior no debe quedar sobredimensionada en altura.");
                }
                const menuBrand = document.querySelector(".o_main_navbar .o_menu_brand");
                if (menuBrand) {
                    const menuBrandHeight = parseFloat(window.getComputedStyle(menuBrand).height);
                    const navbarEntryHeight = parseFloat(navbarEntryStyle.height);
                    if (Math.abs(menuBrandHeight - navbarEntryHeight) > 4) {
                        throw new Error(
                            "El título de la app y las entradas del menú superior deben mantener una altura visual homogénea."
                        );
                    }
                }
            },
        },
    ],
});

