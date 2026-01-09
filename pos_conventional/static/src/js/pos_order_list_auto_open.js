/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Servicio para abrir automáticamente un pedido nuevo cuando se vuelve a la lista
 */
const posConventionalAutoOpenService = {
    dependencies: ["action"],

    start(env, { action }) {
        // Verificar periódicamente si hay un pedido pendiente
        const checkPendingOrder = () => {
            const pendingOrderId = sessionStorage.getItem('pos_conventional_new_order_id');
            const sessionId = sessionStorage.getItem('pos_conventional_session_id');
            const configId = sessionStorage.getItem('pos_conventional_config_id');

            if (pendingOrderId) {
                // Verificar que estamos en la URL correcta
                const currentUrl = window.location.href;
                if (currentUrl.includes('model=pos.order') && currentUrl.includes('view_type=list')) {
                    console.log("POS Conventional: Pedido pendiente detectado:", pendingOrderId);

                    // Limpiar sessionStorage
                    sessionStorage.removeItem('pos_conventional_new_order_id');
                    sessionStorage.removeItem('pos_conventional_session_id');
                    sessionStorage.removeItem('pos_conventional_config_id');

                    // Esperar un poco y abrir el pedido
                    setTimeout(() => {
                        console.log("POS Conventional: Abriendo pedido nuevo...");
                        action.doAction({
                            type: "ir.actions.act_window",
                            res_model: "pos.order",
                            res_id: parseInt(pendingOrderId),
                            views: [[false, "form"]],
                            view_mode: "form",
                            target: "current",
                            context: {
                                // IMPORTANTE: NO incluir default_config_id en el contexto
                                // porque el config_id es un campo computed y puede causar
                                // que pedidos de otras cajas se creen con config_id incorrecto
                                default_session_id: parseInt(sessionId),
                                form_view_initial_mode: 'edit',
                            },
                        });
                    }, 600);
                }
            }
        };

        // Verificar cada 500ms
        const interval = setInterval(checkPendingOrder, 500);

        // Limpiar el intervalo después de 5 segundos (10 intentos)
        setTimeout(() => {
            clearInterval(interval);
        }, 5000);

        return {};
    },
};

registry.category("services").add("pos_conventional_auto_open", posConventionalAutoOpenService);




