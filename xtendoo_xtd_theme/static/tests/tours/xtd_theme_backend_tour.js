import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("xtd_theme_backend_tour", {
    url: "/odoo/action-xtendoo_xtd_theme.action_xtd_dashboard",
    steps: () => [
        // --- Dashboard: carga, edición, ocultar bloque y aviso de cambios sin guardar
        { trigger: ".o_xtd_dashboard .kpi-card" },
        {
            trigger: ".o_xtd_dashboard h2",
            run() {
                const greeting = document.querySelector(".o_xtd_dashboard h2").textContent.trim();
                if (/^Hola,?$/.test(greeting)) {
                    throw new Error("El saludo del dashboard debe incluir el nombre del usuario.");
                }
            },
        },
        { trigger: ".o_xtd_dashboard button:contains('Editar dashboard')", run: "click" },
        { trigger: ".xtd-dashboard-block-controls" },
        {
            trigger: ".xtd-dashboard-block-controls button[title='Ocultar bloque']",
            run: "click",
        },
        { trigger: ".xtd-dashboard-block-hidden" },
        { trigger: ".o_xtd_dashboard .badge:contains('Cambios sin guardar')" },
        {
            // Arrastrar el primer bloque a la mitad derecha del tercero: debe
            // quedar detrás de él y el resto desplazarse.
            trigger: ".o_xtd_dashboard [data-block-key]",
            run() {
                const keys = () => [...document.querySelectorAll(".o_xtd_dashboard [data-block-key]")]
                    .map((el) => el.dataset.blockKey);
                const before = keys();
                const row = document.querySelector(".o_xtd_dashboard [data-block-key]").parentElement;
                const first = document.querySelector(".o_xtd_dashboard [data-block-key] .xtd-dashboard-block-controls");
                const target = document.querySelectorAll(".o_xtd_dashboard [data-block-key]")[2];
                const rect = target.getBoundingClientRect();
                const dataTransfer = new DataTransfer();
                const fire = (el, type) => el.dispatchEvent(new DragEvent(type, {
                    bubbles: true,
                    cancelable: true,
                    dataTransfer,
                    clientX: rect.right - 5,
                    clientY: rect.top + rect.height / 2,
                }));
                fire(first, "dragstart");
                fire(row, "dragover");
                fire(row, "drop");
                fire(first, "dragend");
                window.__xtdDragBefore = before;
            },
        },
        {
            trigger: ".o_xtd_dashboard [data-block-key]",
            run() {
                const after = [...document.querySelectorAll(".o_xtd_dashboard [data-block-key]")]
                    .map((el) => el.dataset.blockKey);
                const before = window.__xtdDragBefore;
                if (after.join() === before.join()) {
                    throw new Error("Arrastrar un bloque no ha cambiado el orden.");
                }
                if (after[2] !== before[0]) {
                    throw new Error(`El bloque arrastrado debía quedar detrás del tercero: ${after}`);
                }
            },
        },
        { trigger: ".o_xtd_dashboard button:contains('Cancelar')", run: "click" },
        { trigger: ".modal .btn-primary", run: "click" },
        { trigger: ".o_xtd_dashboard:not(:has(.xtd-dashboard-block-controls))" },
        // --- Calendario: carga con el estilo Xtd (botones redondeados, sin errores de JS/SCSS)
        {
            trigger: ".o_xtd_dashboard",
            run() {
                odoo.__WOWL_DEBUG__.root.env.services.action.doAction("calendar.action_calendar_event");
            },
        },
        { trigger: ".o_calendar_renderer .fc-timegrid" },
        {
            // Nunca debe sombrearse la semana entera como "no laborable".
            trigger: ".o_calendar_renderer .fc-timegrid-col.fc-day",
            run() {
                const total = document.querySelectorAll(".o_calendar_renderer .fc-timegrid-col.fc-day").length;
                const disabled = document.querySelectorAll(".o_calendar_renderer .fc-timegrid-col.fc-day.o_calendar_disabled").length;
                if (total && total === disabled) {
                    throw new Error("Todos los días del calendario aparecen sombreados como no laborables.");
                }
            },
        },
        {
            // Sin eventos de todo el día, esa fila no debe ocupar espacio de más.
            trigger: ".o_calendar_renderer .fc-scrollgrid-section-body:not(.fc-scrollgrid-section-liquid)",
            run() {
                const row = document.querySelector(
                    ".o_calendar_renderer .fc-scrollgrid-section-body:not(.fc-scrollgrid-section-liquid)"
                );
                if (!document.querySelector(".o_calendar_renderer .fc-daygrid-event-harness") && row.offsetHeight > 30) {
                    throw new Error(`La fila de todo el día ocupa demasiado (${row.offsetHeight}px).`);
                }
            },
        },
        {
            // Franja 9:00-18:00 del usuario: no hay filas fuera de ella.
            trigger: ".o_calendar_renderer .fc-timegrid-slot-label[data-time='10:00:00']",
            run() {
                const hasSlot = (time) => !!document.querySelector(
                    `.o_calendar_renderer .fc-timegrid-slot-label[data-time='${time}']`
                );
                if (hasSlot("08:00:00") || hasSlot("18:00:00")) {
                    throw new Error("El calendario debe ocultar las horas fuera de la franja del usuario.");
                }
            },
        },
        {
            trigger: ".o_calendar_header .o_calendar_button_today",
            run() {
                const radius = parseFloat(
                    window.getComputedStyle(document.querySelector(".o_calendar_button_today")).borderTopLeftRadius
                );
                if (!(radius >= 20)) {
                    throw new Error("Los botones del calendario deben tener el estilo redondeado Xtd.");
                }
            },
        },
        // --- Ajustes: el tema de la pestaña activa y de la navbar
        {
            trigger: ".o_main_navbar",
            run() {
                const menuService = odoo.__WOWL_DEBUG__.root.env.services.menu;
                menuService.selectMenu(
                    menuService.getApps().find((app) => app.xmlid === "base.menu_administration")
                );
            },
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
            trigger: ".o_base_settings_view",
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
                if (!activeTabStyle.boxShadow.includes("244, 87, 0")) {
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

