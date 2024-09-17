/** @odoo-module **/

import {Component} from "@odoo/owl";
import {ProductScreen} from "@point_of_sale/app/screens/product_screen/product_screen";
import {useService} from "@web/core/utils/hooks";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";

export class CreateOrderButton extends Component {
    setup() {
        this.popup = useService("popup");
        this.pos = useService("pos");
        this.ui = useService("ui");  // Servicio UI para bloquear/desbloquear
        this.orm = useService("orm");  // Servicio ORM para interactuar con el backend
        this.report = useService("report");  // Servicio Report para imprimir el albarán
    }

    async onClick() {
        const currentOrder = this.pos.get_order();

        // Verificar si hay un cliente seleccionado
        if (!currentOrder.get_partner()) {
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: "Seleccione el cliente",
                body: "Debe seleccionar el cliente antes de crear el pedido y el albarán.",
            });
            if (confirmed) {
                await this.selectPartner();
            }
            return;
        }

        // Verificar si hay líneas de pedido
        if (currentOrder.get_orderlines().length === 0) {
            this.popup.add(ErrorPopup, {
                title: "Seleccione algún producto",
                body: "No hay productos en la venta.",
            });
            return;
        }

        // Mostrar ConfirmPopup para confirmar la creación del pedido
        const { confirmed } = await this.popup.add(ConfirmPopup, {
            title: "Crear Pedido y Albarán",
            body: "¿Está seguro de que desea crear el pedido y el albarán?",
        });

        // Si el usuario confirma, realizar la creación del pedido
        if (confirmed) {
            await this.createDeliveredSaleOrder();
        }
    }

    async createDeliveredSaleOrder() {
        await this._actionCreateSaleOrder("delivered");
    }

    async _actionCreateSaleOrder(order_state) {
        const current_order = this.pos.get_order();

        // Bloquear la interfaz mientras se crea la orden
        this.ui.block();

        try {
            // Crear la orden de venta llamando al ORM
            const result = await this.orm.call("sale.order", "create_order_from_pos", [
                current_order.export_as_JSON(),
                order_state,
            ]);

            // Eliminar la orden actual del POS y crear una nueva
            this.pos.removeOrder(current_order);
            this.pos.add_new_order();

            syncOrderResult = await this.pos.push_single_order(this.currentOrder);
            console.log("syncOrderResult", syncOrderResult);
           // Verificar si se ha creado un picking y generar el reporte si es así
        if (result.picking_id) {
            console.log("Generating picking report for ID:", result.picking_id);

            // Generar el reporte del picking
            await this.report.doAction("stock.action_report_delivery", [
                 syncOrderResult[0].stock_picking,
           ]);

            console.log("Picking report generated");
        } else {
            console.error("No picking ID returned from create_order_from_pos");
        }
    } catch (error) {
        console.error("Error al crear el pedido:", error);
    } finally {
        // Desbloquear la interfaz
        this.ui.unblock();
    }
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
            currentOrder.set_partner(newPartner);
        }
    }
}

CreateOrderButton.template = "pos_order_to_sale_order.CreateOrderButton";

// Mostrar el botón siempre sin condiciones
ProductScreen.addControlButton({
    component: CreateOrderButton,
});
