/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Acción de cliente para crear automáticamente un nuevo pedido POS
 * después de completar el flujo de pago.
 * Crea el pedido en el backend y lo abre automáticamente.
 */
async function posConventionalNewOrder(env, action) {
    const { config_id, session_id } = action.params;

    try {
        const orm = env.services.orm;
        const actionService = env.services.action;

        // Crear el nuevo pedido en el backend para que tenga nombre real
        const newOrderId = await orm.call(
            "pos.order",
            "create_new_order_for_conventional_pos",
            [],
            {
                session_id: session_id,
                config_id: config_id,
            }
        );

        // Forzar recarga del registro para obtener el nombre actualizado
        await orm.call("pos.order", "invalidate_model", [[newOrderId]]);

        // Abrir el pedido recién creado
        return actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "pos.order",
            res_id: newOrderId,
            views: [[false, "form"]],
            view_mode: "form",
            target: "current",
        });
    } catch (error) {
        console.error("Error al crear y abrir nuevo pedido:", error);
        // Fallback: abrir formulario sin crear primero
        return env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "pos.order",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_session_id: session_id,
                default_config_id: config_id,
                default_state: "draft",
            },
        });
    }
}

registry.category("actions").add("pos_conventional_new_order", posConventionalNewOrder);

