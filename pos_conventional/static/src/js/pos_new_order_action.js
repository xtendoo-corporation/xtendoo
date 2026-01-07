/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Acción de cliente para nuevo pedido en POS Conventional
 * Simplemente vuelve atrás a la lista de pedidos
 */
async function posConventionalNewOrder(env, action) {
    window.history.back();
    return { type: "ir.actions.act_window_close" };
}

registry.category("actions").add("pos_conventional_new_order", posConventionalNewOrder);
