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

    // 2. Abrir el formulario de nuevo pedido encima.
    await actionService.doAction("point_of_sale.action_pos_pos_form", {
        viewType: 'form',
        props: { resId: false },
        additionalContext: context
    });
}

registry.category("actions").add("pos_conventional_new_order", posConventionalNewOrder);
