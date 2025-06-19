/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

// En Odoo 18, el registry es el método preferido para registrar tours
registry.category("web_tour.tours").add("activate_spanish_language_tour", {
    url: "/web",
    rainbowMan: true,
    rainbowManMessage: _t('¡Felicidades! El idioma español está ahora activo en su sistema.'),
    sequence: 10,
    steps: [
        {
            trigger: '.o_menu_toggle, .o_menu_sections [data-menu-xmlid="base.menu_administration"]',
            content: _t('Empecemos haciendo clic en el menú <b>Ajustes</b>'),
            position: 'bottom',
        },
        {
            trigger: '[data-menu-xmlid="base.menu_management"]',
            content: _t('Ahora, haga clic en <b>Usuarios y Empresas</b>'),
            position: 'right',
        },
        {
            trigger: '[data-menu-xmlid="base.menu_users"]',
            content: _t('A continuación, haga clic en <b>Usuarios</b>'),
            position: 'right',
        },
        {
            trigger: '.o_data_row:first',
            content: _t('Haga clic en su usuario para editarlo'),
            position: 'bottom',
        },
        {
            trigger: 'button.btn-primary:contains("Editar"), button.o_form_button_edit',
            extra_trigger: '.o_form_view',
            content: _t('Haga clic en Editar para modificar las preferencias de usuario'),
            position: 'bottom',
        },
        {
            trigger: 'div[name="lang"] input, select[name="lang"]',
            content: _t('Haga clic aquí para seleccionar el idioma'),
            position: 'bottom',
        },
        {
            trigger: 'li:contains("Spanish"), option:contains("Spanish")',
            extra_trigger: '.dropdown-menu, select[name="lang"]',
            content: _t('Seleccione Español de la lista'),
            position: 'bottom',
        },
        {
            trigger: '.o_form_button_save, button.btn-primary:contains("Guardar")',
            content: _t('Guarde los cambios'),
            position: 'bottom',
        },
        {
            trigger: '.o_menu_apps',
            content: _t('¡Bien! Ahora haga clic en el menú principal para refrescar la interfaz.'),
            position: 'bottom',
        },
    ]
});
