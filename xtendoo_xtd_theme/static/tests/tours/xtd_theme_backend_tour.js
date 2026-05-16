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
    ],
});

