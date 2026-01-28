/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Acción de cliente para nuevo pedido en POS Conventional
 * Simplemente vuelve atrás a la lista de pedidos
 */
async function posConventionalNewOrder(env, action) {
    const actionService = env.services.action;
    const context = action.params || {};

    // 1. Ir a la vista de lista (Pedidos) cargando el CONTEXTO correcto para que los botones funcionen
    await actionService.doAction("point_of_sale.action_pos_pos_form", {
        clearBreadcrumbs: true,
        viewType: 'list',
        additionalContext: context
    });

    // 2. Comprobar si debemos forzar login (PIN) para el nuevo pedido
    // Esto viene del backend tras confirmar un pago con la opción activada
    if (context.force_login_after_order) {
        await actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'pos.session.pin.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_session_id: context.default_session_id,
                force_new_order_flow: true,
                no_cancel: true,
            }
        });
    } else {
        // 3. Abrir el formulario de nuevo pedido directamente (flujo normal)
        await actionService.doAction("point_of_sale.action_pos_pos_form", {
            viewType: 'form',
            props: { resId: false },
            additionalContext: context
        });
    }
}

registry.category("actions").add("pos_conventional_new_order", posConventionalNewOrder);
