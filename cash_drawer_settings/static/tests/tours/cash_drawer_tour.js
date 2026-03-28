/** @odoo-module **/
/**
 * Tour JS para verificar la integración del cajón portamonedas en el TPV.
 *
 * Ejecutar con:
 *   python odoo-bin --test-enable --test-tags=point_of_sale \
 *     -u cash_drawer_settings --stop-after-init
 */

import { registry } from "@web/core/registry";

/**
 * Tour 1: Verificar que el botón aparece en el menú hamburguesa del TPV
 * cuando cash_drawer_pos_enabled = true.
 */
registry.category("web_tour.tours").add("cash_drawer_pos_button_visible", {
    url: "/pos/ui",
    steps: () => [
        // Abrir el menú hamburguesa
        {
            content: "Abrir menú hamburguesa del TPV",
            trigger: ".pos-topheader button .fa-bars",
            run: "click",
        },
        // Verificar que el botón de apertura de cajón está visible
        {
            content: "Verificar que el botón 'Abrir cajón portamonedas' está presente",
            trigger: ".pos-burger-menu-items .dropdown-item:contains('Abrir cajón portamonedas')",
            run: () => {
                console.log(
                    "[CashDrawerTour] ✅ Botón de cajón portamonedas encontrado en el menú"
                );
            },
        },
    ],
});

/**
 * Tour 2: Verificar que el botón NO aparece cuando cash_drawer_pos_enabled = false.
 */
registry.category("web_tour.tours").add("cash_drawer_pos_button_hidden", {
    url: "/pos/ui",
    steps: () => [
        // Abrir el menú hamburguesa
        {
            content: "Abrir menú hamburguesa del TPV",
            trigger: ".pos-topheader button .fa-bars",
            run: "click",
        },
        // Verificar que NO aparece el botón de cajón
        {
            content: "Verificar que el botón de cajón está oculto",
            trigger: ".pos-burger-menu-items",
            run: () => {
                const items = document.querySelectorAll(
                    ".pos-burger-menu-items .dropdown-item"
                );
                const found = Array.from(items).some((el) =>
                    el.textContent.includes("Abrir cajón portamonedas")
                );
                if (found) {
                    throw new Error(
                        "El botón de cajón portamonedas NO debería estar visible " +
                        "cuando cash_drawer_pos_enabled = false"
                    );
                }
                console.log(
                    "[CashDrawerTour] ✅ Botón de cajón correctamente oculto"
                );
            },
        },
    ],
});

/**
 * Tour 3: Verificar que el botón de vincular USB aparece en navegadores
 * con WebUSB (Chrome/Edge). Este tour solo se usa en entornos donde
 * WebUSB está disponible.
 */
registry.category("web_tour.tours").add("cash_drawer_webusb_button", {
    url: "/pos/ui",
    steps: () => [
        {
            content: "Abrir menú hamburguesa",
            trigger: ".pos-topheader button .fa-bars",
            run: "click",
        },
        {
            content: "Verificar que el botón 'Vincular impresora USB' está presente",
            trigger: ".pos-burger-menu-items .dropdown-item:contains('Vincular impresora USB')",
            run: () => {
                console.log(
                    "[CashDrawerTour] ✅ Botón de vinculación USB encontrado"
                );
            },
        },
    ],
});

