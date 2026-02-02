/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class PosOrderListController extends ListController {
    setup() {
        super.setup();

        // Estado reactivo para controlar la visibilidad de los botones
        this.state = useState({
            showCloseButton: false
        });

        // Variable interna para trackear la sesión activa actual
        this.activeSessionId = null;

        // Handler para guardar la sesión antes de un reload
        this.handleBeforeUnload = () => {
            if (this.activeSessionId) {
                // Solo guardamos si tenemos un ID activo.
                // Si estamos en una vista "limpia" (sin ID), no guardamos nada,
                // asegurando que el storage quede limpio.
                sessionStorage.setItem('pos_conventional_active_session_id', this.activeSessionId);
            }
        };

        // Registrar el listener para sobrevivir a reloads (F5)
        window.addEventListener('beforeunload', this.handleBeforeUnload);

        onWillStart(async () => {
            // Verificar si estamos dentro de una caja no táctil abierta
            await this.checkIfInsideNonTouchSession();
        });

        onWillUnmount(() => {
            window.removeEventListener('beforeunload', this.handleBeforeUnload);
        });
    }

    /**
     * Intercepta la apertura de un registro para redirigir al sale.order vinculado
     * cuando el pedido está vinculado a un sale.order
     */
    async openRecord(record, mode) {
        // Obtener el campo linked_sale_order_id del registro
        const linkedSaleOrderField = record.data.linked_sale_order_id;

        // Log para depuración
        console.log('openRecord - linkedSaleOrderField:', linkedSaleOrderField);
        console.log('openRecord - record.data:', record.data);

        // Si el pedido está vinculado a un sale.order, abrir ese sale.order
        if (linkedSaleOrderField) {
            let saleOrderId = null;

            // El campo Many2one puede venir en diferentes formatos:
            // - Array [id, name]
            // - Objeto {id: X, display_name: "..."}
            // - Número directo
            if (Array.isArray(linkedSaleOrderField)) {
                saleOrderId = linkedSaleOrderField[0];
            } else if (typeof linkedSaleOrderField === 'object' && linkedSaleOrderField.id) {
                saleOrderId = linkedSaleOrderField.id;
            } else if (typeof linkedSaleOrderField === 'number') {
                saleOrderId = linkedSaleOrderField;
            }

            console.log('openRecord - saleOrderId calculado:', saleOrderId, typeof saleOrderId);

            if (saleOrderId && typeof saleOrderId === 'number') {
                await this.env.services.action.doAction({
                    type: 'ir.actions.act_window',
                    res_model: 'sale.order',
                    res_id: saleOrderId,
                    views: [[false, 'form']],
                    view_mode: 'form',
                    target: 'current',
                });
                return;
            }
        }

        // Si no está vinculado, comportamiento normal (abrir pos.order)
        return super.openRecord(record, mode);
    }

    /**
     * Verifica si estamos dentro de una caja no táctil abierta.
     * Los botones de cerrar caja, entrada/salida de efectivo solo deben mostrarse
     * cuando accedemos desde una caja no táctil, no desde el menú general de pedidos.
     */
    async checkIfInsideNonTouchSession() {
        // 1. Recuperar contexto original
        const context = this.props.context || {};
        let sessionId = context.default_session_id;

        // 2. Comprobar recuperación de emergencia (Reload)
        // Leemos e INMEDIATAMENTE borramos para evitar que una navegación SPA posterior lo lea.
        // Esto soluciona el problema de que 'performance.navigation.type' no es fiable en SPA.
        const storedSessionId = sessionStorage.getItem('pos_conventional_active_session_id');
        sessionStorage.removeItem('pos_conventional_active_session_id');

        if (!sessionId && storedSessionId) {
            sessionId = parseInt(storedSessionId);
            console.log('checkIfInsideNonTouchSession - Session ID recuperado (Restore):', sessionId);
        }

        // Guardamos en la variable de instancia para el beforeunload (para reloads futuros)
        this.activeSessionId = sessionId;

        if (!sessionId) {
            this.state.showCloseButton = false;
            return;
        }

        try {
            // Verificar que la sesión existe, está abierta y es de una caja no táctil
            const sessionData = await this.model.orm.read(
                "pos.session",
                [sessionId],
                ["state", "config_id"]
            );

            if (sessionData && sessionData.length > 0) {
                const session = sessionData[0];

                // Verificar si la sesión está abierta
                if (session.state === 'opened' || session.state === 'opening_control') {
                    // Verificar config
                    if (session.config_id) {
                        const configId = Array.isArray(session.config_id)
                            ? session.config_id[0]
                            : session.config_id;

                        const configData = await this.model.orm.read(
                            "pos.config",
                            [configId],
                            ["pos_non_touch", "pos_force_employee_login_after_order"]
                        );

                        if (configData && configData.length > 0) {
                            const config = configData[0];

                            // 1. Botones para modo no táctil
                            if (config.pos_non_touch) {
                                this.state.showCloseButton = true;
                            }

                            // 2. Guardar configuración de PIN forzado para usar en createRecord
                            this.forceLogin = config.pos_force_employee_login_after_order;
                            this.currentSessionId = sessionId; // Guardar ID para usarlo después
                        }
                    }
                }
            }
        } catch (error) {
            console.error("Error verificando sesión no táctil:", error);
        }
    }

    /**
     * Sobrescribimos createRecord para interceptar el botón "Nuevo"
     */
    async createRecord() {
        if (this.forceLogin && this.currentSessionId) {
            // Si está activada la opción, abrir wizard de PIN en lugar del form directo
            const action = {
                name: _t("Introducir PIN"),
                type: 'ir.actions.act_window',
                res_model: 'pos.session.pin.wizard',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_session_id: this.currentSessionId,
                    force_new_order_flow: true, // Flag para indicar flujo de nuevo pedido
                    no_cancel: true,            // Flag para ocultar cancelar (hacerlo obligatorio)
                }
            };
            await this.env.services.action.doAction(action);
        } else {
            // Comportamiento normal
            super.createRecord();
        }
    }

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

    /**
     * Maneja el click en el botón "Entrada / Salida de efectivo"
     */
    async onCashInOut() {
        try {
            // Llamar al método del modelo pos.order que abre el wizard de entrada/salida
            const result = await this.model.orm.call(
                "pos.order",
                "action_cash_in_out_wizard",
                [[]]
            );

            if (result && result.type) {
                // Protección: algunos actions pueden no traer `views` y el frontend espera que exista
                if (!result.views) {
                    // Añadir una vista por defecto para evitar errores en _preprocessAction
                    result.views = [[false, 'form']];
                }
                await this.env.services.action.doAction(result);
            } else {
                // Si no devuelve acción, mostrar notificación
                this.env.services.notification.add(
                    "Acción de entrada/salida ejecutada",
                    { type: "success" }
                );
            }
        } catch (error) {
            console.error("Error en Entrada/Salida de efectivo:", error);
            this.env.services.notification.add(
                error.message || "Error al intentar abrir Entrada/Salida de efectivo",
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
