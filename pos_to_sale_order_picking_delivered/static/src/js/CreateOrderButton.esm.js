/** @odoo-module */

import {Component} from "@odoo/owl";
import {CreateOrderPopup} from "./CreateOrderPopup.esm";
import {ProductScreen} from "@point_of_sale/app/screens/product_screen/product_screen";
import {useService} from "@web/core/utils/hooks";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";

export class CreateOrderButton extends Component {
    setup() {
        this.popup = useService("popup");
        this.pos = useService("pos");  // Servicio POS para obtener el estado de la sesión de punto de venta
    }

    async onClick() {  // Marcar onClick como función asincrónica
        const currentOrder = this.pos.get_order();  // Obtener la orden actual

        // Verificar si hay un cliente seleccionado
        if (!currentOrder.get_partner()) {
            // Usar ConfirmPopup para mostrar un mensaje y obtener la confirmación
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: "Seleccione el cliente",
                body: "Debe seleccionar el cliente antes de crear el pedido y el albarán.",
            });
            if (confirmed) {
                // Abrir el selector de clientes si se confirma
                await this.selectPartner();
            }
            return;
        }

        // Verificar si hay líneas de pedido
        if (currentOrder.get_orderlines().length === 0) {
            // Usar ErrorPopup para mostrar errores
            this.popup.add(ErrorPopup, {
                title: "Seleccione algún producto",
                body: "No hay productos en la venta.",
            });
            return;
        }

        // Si todo está bien, mostrar el popup de creación de orden
        this.popup.add(CreateOrderPopup, { zIndex: 1069 });
    }

    async selectPartner(isEditMode = false, missingFields = []) {
        const currentOrder = this.pos.get_order();
        const currentPartner = currentOrder.get_partner();
        const partnerScreenProps = { partner: currentPartner };

        if (isEditMode && currentPartner) {
            partnerScreenProps.editModeProps = true;
            partnerScreenProps.missingFields = missingFields;
        }

        // Mostrar pantalla de selección de cliente
        const { confirmed, payload: newPartner } = await this.pos.showTempScreen(
            "PartnerListScreen",
            partnerScreenProps
        );
        if (confirmed) {
            currentOrder.set_partner(newPartner);  // Asignar el nuevo cliente a la orden
        }
    }
}

CreateOrderButton.template = "pos_order_to_sale_order.CreateOrderButton";

// Mostrar el botón siempre sin condiciones
ProductScreen.addControlButton({
    component: CreateOrderButton,
});
