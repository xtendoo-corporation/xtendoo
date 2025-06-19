/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { Component, onMounted } from "@odoo/owl";

/**
 * Acción cliente para iniciar el tour de activación del idioma español
 */
class ActivateSpanishTourAction extends Component {
    setup() {
        onMounted(() => {
            // Obtener el servicio de tour a través del registry
            const tourService = registry.category("services").get("tour");

            // Iniciar el tour
            tourService.start("activate_spanish_language_tour");

            // Redirigir a la página principal después de un pequeño retraso
            setTimeout(() => {
                browser.location.href = "/web";
            }, 1000);
        });
    }
}

// Registrar la acción cliente
registry.category("actions").add("xtendoo_activate_spanish_tour", ActivateSpanishTourAction);

export default ActivateSpanishTourAction;
