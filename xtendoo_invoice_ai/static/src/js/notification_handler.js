/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Manejador de notificaciones para mostrar mensajes después de acciones
 * Se registra como un servicio para poder mostrar notificaciones desde el contexto
 */
export const notificationHandlerService = {
    dependencies: ["notification", "action"],

    start(env, { notification, action }) {
        // Interceptar acciones para mostrar notificaciones del contexto
        const originalDoAction = action.doAction;

        action.doAction = async function(actionRequest, options = {}) {
            // Verificar si hay una notificación en el contexto de la acción
            if (actionRequest && typeof actionRequest === 'object') {
                const context = actionRequest.context || {};

                // Mostrar notificación si existe
                if (context.notification) {
                    const notif = context.notification;
                    notification.add(
                        notif.message || notif.text || "Action completed",
                        {
                            title: notif.title,
                            type: notif.type || "info",
                            sticky: notif.sticky !== undefined ? notif.sticky : false,
                        }
                    );

                    // Eliminar la notificación del contexto para evitar que se propague
                    delete context.notification;
                }

                // Manejar notificaciones en params (para acciones de tipo client)
                if (actionRequest.params && actionRequest.params.notification) {
                    const notif = actionRequest.params.notification;
                    notification.add(
                        notif.message || notif.text || "Action completed",
                        {
                            title: notif.title,
                            type: notif.type || "info",
                            sticky: notif.sticky !== undefined ? notif.sticky : false,
                        }
                    );

                    delete actionRequest.params.notification;
                }
            }

            // Llamar a la acción original
            return originalDoAction.call(this, actionRequest, options);
        };

        return {};
    },
};

registry.category("services").add("xtendoo_invoice_ai_notification_handler", notificationHandlerService);

