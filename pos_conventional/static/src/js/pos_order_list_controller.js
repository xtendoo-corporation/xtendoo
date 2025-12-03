/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";

export class PosOrderListController extends ListController {
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
}

// Registrar el controller en el registry
export const posOrderListView = {
    ...listView,
    Controller: PosOrderListController,
};

registry.category("views").add("button_in_tree", posOrderListView);
