/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Acción de cliente para redirigir a la lista de pedidos
 * después de completar el flujo de pago.
 * Restaura la acción anterior del breadcrumb para mantener el contexto del POS.
 */
async function posConventionalNewOrder(env, action) {
    const { config_id, session_id } = action.params;

    try {
        const actionService = env.services.action;

        // Obtener el stack de acciones (breadcrumb)
        const actionStack = actionService.currentController?.action?.jsId
            ? [...(actionService.actions || [])]
            : [];

        // Si hay al menos 2 acciones en el stack (la actual y la anterior)
        // restaurar la acción anterior (la lista de pedidos)
        if (actionStack.length >= 2) {
            const previousAction = actionStack[actionStack.length - 2];
            if (previousAction && previousAction.jsId) {
                // Restaurar la acción anterior (equivalente a hacer clic en el breadcrumb)
                await actionService.restore(previousAction.jsId);
                return;
            }
        }

        // Si no funciona el método anterior, intentar usar switchView para volver a la lista
        const currentController = actionService.currentController;
        if (currentController && currentController.action && currentController.action.type === 'ir.actions.act_window') {
            // Cambiar a la vista de lista
            try {
                await actionService.switchView("list");
                return;
            } catch (e) {
                console.warn("No se pudo cambiar a vista de lista:", e);
            }
        }

        // Fallback final: usar router.back() como último recurso
        const router = env.services.router;
        if (window.history.length > 1) {
            router.back();
        } else {
            // Último fallback: crear una nueva acción para ir a la lista
            return actionService.doAction({
                type: "ir.actions.act_window",
                name: "Pedidos",
                res_model: "pos.order",
                views: [[false, "list"], [false, "form"]],
                view_mode: "list,form",
                target: "current",
                context: {
                    default_session_id: session_id,
                    default_config_id: config_id,
                },
                domain: [["session_id", "=", session_id]],
            });
        }
    } catch (error) {
        console.error("Error al redirigir a la lista de pedidos:", error);
        // Fallback: usar router.back()
        try {
            const router = env.services.router;
            router.back();
        } catch (e) {
            console.error("Error en fallback:", e);
        }
    }
}

registry.category("actions").add("pos_conventional_new_order", posConventionalNewOrder);

