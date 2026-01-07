/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch del ListController para abrir automáticamente un pedido nuevo
 * cuando se vuelve a la lista después de cerrar un pedido.
 */
patch(ListController.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");

        // Verificar si hay un pedido pendiente de abrir después de volver a la lista
        this.checkAndOpenPendingOrder();
    },

    checkAndOpenPendingOrder() {
        // Solo aplicar esto para pos.order
        if (this.props.resModel !== "pos.order") {
            return;
        }

        // Verificar si hay un pedido guardado en sessionStorage
        const pendingOrderId = sessionStorage.getItem('pos_conventional_new_order_id');
        const sessionId = sessionStorage.getItem('pos_conventional_session_id');
        const configId = sessionStorage.getItem('pos_conventional_config_id');

        if (pendingOrderId) {
            console.log("POS Conventional: Pedido pendiente detectado:", pendingOrderId);

            // Limpiar sessionStorage
            sessionStorage.removeItem('pos_conventional_new_order_id');
            sessionStorage.removeItem('pos_conventional_session_id');
            sessionStorage.removeItem('pos_conventional_config_id');

            // Esperar un momento para que la lista se cargue completamente
            setTimeout(() => {
                console.log("POS Conventional: Abriendo pedido nuevo...");
                this.actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: "pos.order",
                    res_id: parseInt(pendingOrderId),
                    views: [[false, "form"]],
                    view_mode: "form",
                    target: "current",
                    context: {
                        default_session_id: parseInt(sessionId),
                        default_config_id: parseInt(configId),
                        form_view_initial_mode: 'edit',
                    },
                });
            }, 500);
        }
    },
});

