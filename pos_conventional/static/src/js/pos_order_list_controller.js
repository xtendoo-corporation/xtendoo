/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { useState, onWillStart } from "@odoo/owl";

export class PosOrderListController extends ListController {
    setup() {
        super.setup();

        // Estado reactivo para controlar la visibilidad del botón
        this.state = useState({
            showCloseButton: false
        });

        onWillStart(async () => {
            // Verificar si el domain incluye config_id (viene de nuestra redirección)
            this.checkDomain();
        });
    }

    /**
     * Verifica si el domain actual incluye filtro por config_id
     * Esto indica que venimos de la redirección de una caja no táctil
     */
    checkDomain() {
        const domain = this.props.domain || [];

        // Buscar si hay un filtro por config_id en el domain
        const hasConfigFilter = domain.some(clause => {
            if (Array.isArray(clause) && clause.length === 3) {
                return clause[0] === 'config_id';
            }
            return false;
        });

        this.state.showCloseButton = hasConfigFilter;
    }

    /**
     * Maneja el click en el botón "Cerrar caja"
     */
    async onCloseCashRegister() {
        try {
            // Llamar al método del modelo pos.order que gestiona el cierre
            const result = await this.model.orm.call(
                "pos.order",
                "action_close_pos_session_wizard",
                [[]]  // Array vacío porque no necesitamos IDs específicos
            );

            // Si devuelve una acción (el wizard), ejecutarla
            if (result && result.type) {
                await this.env.services.action.doAction(result);
            }
        } catch (error) {
            console.error("Error al cerrar caja:", error);
            // Mostrar error al usuario
            this.env.services.notification.add(
                error.message || "Error al intentar cerrar la caja",
                { type: "danger" }
            );
        }
    }

    /**
     * Maneja el click en el botón "Entrada / Salida de efectivo"
     */
    async onCashInOut() {
        try {
            // Llamar al método del modelo pos.order que abre el wizard de entrada/salida
            const result = await this.model.orm.call(
                "pos.order",
                "action_cash_in_out_wizard",
                [[]]
            );

            if (result && result.type) {
                // Protección: algunos actions pueden no traer `views` y el frontend espera que exista
                if (!result.views) {
                    // Añadir una vista por defecto para evitar errores en _preprocessAction
                    result.views = [[false, 'form']];
                }
                await this.env.services.action.doAction(result);
            } else {
                // Si no devuelve acción, mostrar notificación
                this.env.services.notification.add(
                    "Acción de entrada/salida ejecutada",
                    { type: "success" }
                );
            }
        } catch (error) {
            console.error("Error en Entrada/Salida de efectivo:", error);
            this.env.services.notification.add(
                error.message || "Error al intentar abrir Entrada/Salida de efectivo",
                { type: "danger" }
            );
        }
    }
}

// Registrar el controller en el registry
export const posOrderListView = {
    ...listView,
    Controller: PosOrderListController,
};

registry.category("views").add("button_in_tree", posOrderListView);
