/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";

export class PosPaymentButtons extends Component {
    static template = "pos_conventional.PosPaymentButtons";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            methods: [],
        });

        onWillStart(async () => {
            await this.updateMethods(this.props);
        });

        onWillUpdateProps(async (nextProps) => {
            await this.updateMethods(nextProps);
        });
    }

    async updateMethods(props) {
        const fieldData = props.record.data[props.name];
        if (!fieldData || !fieldData.currentIds || fieldData.currentIds.length === 0) {
            this.state.methods = [];
            return;
        }

        const ids = fieldData.currentIds;
        
        // Siempre leemos del servidor para asegurar que tenemos los nombres de TODOS los IDs
        try {
            const methods = await this.orm.read("pos.payment.method", ids, ["name"]);
            // Ordenar por el orden original de IDs si es necesario, 
            // aunque read suele devolver en orden de IDs pasados.
            this.state.methods = methods.map(m => ({
                id: m.id,
                name: m.name,
            }));
        } catch (error) {
            console.error("Error al leer nombres de métodos de pago:", error);
            this.state.methods = ids.map(id => ({ id: id, name: "Metodo " + id }));
        }
    }

    get paymentMethods() {
        return this.state.methods;
    }

    /**
     * Llama a la acción de pago en el servidor para el método seleccionado.
     */
    async onPaymentMethodClick(methodId) {
        // Asegurar que el pedido está guardado antes de pagar
        const saved = await this.props.record.save();
        if (!saved && !this.props.record.resId) {
            return;
        }

        const orderId = this.props.record.resId;
        if (!orderId) {
            console.error("No se pudo obtener el ID del pedido.");
            return;
        }

        try {
            const action = await this.orm.call(
                "pos.order", 
                "action_pay_with_method", 
                [orderId], 
                { payment_method: methodId }
            );
            
            if (action) {
                await this.action.doAction(action);
            } else {
                // Si no hay acción, refrescar el registro por si acaso
                await this.props.record.load();
            }
        } catch (error) {
            console.error("Error al procesar pago:", error);
        }
    }
}

registry.category("fields").add("pos_payment_buttons", {
    component: PosPaymentButtons,
    supportedTypes: ["many2many"],
});
