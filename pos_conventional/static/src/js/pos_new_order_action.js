/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Acción de cliente para crear un nuevo pedido y redirigir a la lista
 * después de completar el flujo de pago.
 */
async function posConventionalNewOrder(env, action) {
    const { config_id, session_id } = action.params;

    try {
        const orm = env.services.orm;

        console.log("POS Conventional: Iniciando flujo de nuevo pedido");

        // PRIMERO: Crear el nuevo pedido en el backend
        console.log("POS Conventional: Creando nuevo pedido...");
        const newOrderId = await orm.call(
            "pos.order",
            "create_new_order_for_conventional_pos",
            [],
            {
                session_id: session_id,
                config_id: config_id,
            }
        );

        console.log("POS Conventional: Pedido creado con ID:", newOrderId);

        // Guardar el ID en sessionStorage para usarlo después de la navegación
        sessionStorage.setItem('pos_conventional_new_order_id', newOrderId);
        sessionStorage.setItem('pos_conventional_session_id', session_id);
        sessionStorage.setItem('pos_conventional_config_id', config_id);

        // SEGUNDO: Volver a la lista usando window.history.back()
        console.log("POS Conventional: Volviendo a la lista con router.back()");
        if (env.services.router && env.services.router.back) {
            env.services.router.back();
        } else {
            // Fallback: usar window.history.back()
            window.history.back();
        }

        // El código no continúa aquí porque router.back() cambia el contexto

    } catch (error) {
        console.error("POS Conventional: Error en el flujo:", error);
        // Fallback: intentar solo volver atrás con window.history
        try {
            window.history.back();
        } catch (e) {
            console.error("POS Conventional: Error en fallback:", e);
        }
    }
}

registry.category("actions").add("pos_conventional_new_order", posConventionalNewOrder);

