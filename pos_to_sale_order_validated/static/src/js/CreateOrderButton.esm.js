/** @odoo-module */

import {Component} from "@odoo/owl";
import {CreateOrderPopup} from "./CreateOrderPopup.esm";
import {ProductScreen} from "@point_of_sale/app/screens/product_screen/product_screen";
import {useService} from "@web/core/utils/hooks";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

export class CreateOrderButton extends Component {
    setup() {
        this.popup = useService("popup");
        this.pos = useService("pos");  // Servicio POS para obtener el estado de la sesión de punto de venta
    }

    onClick() {
        const currentOrder = this.pos.get_order();  // Obtener la orden actual

        // Verificar si hay un cliente seleccionado
        if (!currentOrder.get_partner()) {
            // Usar ErrorPopup para mostrar errores
            this.popup.add(ErrorPopup, {
                title: "Error",
                body: "No hay cliente seleccionado.",
            });
            return;
        }

        // Verificar si hay líneas de pedido
        if (currentOrder.get_orderlines().length === 0) {
            // Usar ErrorPopup para mostrar errores
            this.popup.add(ErrorPopup, {
                title: "Error",
                body: "No hay productos en la venta.",
            });
            return;
        }

        // Si todo está bien, mostrar el popup de creación de orden
        this.popup.add(CreateOrderPopup, { zIndex: 1069 });
    }
}

CreateOrderButton.template = "pos_order_to_sale_order.CreateOrderButton";

// Mostrar el botón siempre sin condiciones
ProductScreen.addControlButton({
    component: CreateOrderButton,
});
