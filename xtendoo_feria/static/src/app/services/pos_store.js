/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(PosStore.prototype, {
    /**
     * Override setPartnerToCurrentOrder to:
     * 1. Check if the partner is already permanently assigned to another table.
     * 2. Write feria_partner_id on the table so the assignment survives
     *    session close, order finalization, browser refresh, etc.
     */
    setPartnerToCurrentOrder(partner) {
        if (this.config.module_pos_restaurant) {
            const currentOrder = this.getOrder();
            const currentTable = currentOrder?.table_id;

            if (partner && currentTable) {
                // Check all tables on all floors for duplicate assignment
                const allTables = this.models["restaurant.table"].getAll();
                for (const table of allTables) {
                    if (!table.active || table.id === currentTable.id) {
                        continue;
                    }
                    if (table.feria_partner_id?.id === partner.id) {
                        this.notification.add(
                            _t("'%s' ya está en la Mesa %s", partner.name, table.table_number),
                            { type: "danger", sticky: true }
                        );
                        return;
                    }
                }
            }

            // Persist the assignment (or clear it) on the table
            if (currentTable) {
                const newPartnerId = partner ? partner.id : false;
                const currentFeriaId = currentTable.feria_partner_id?.id || false;

                if (newPartnerId !== currentFeriaId) {
                    this.data.write("restaurant.table", [currentTable.id], {
                        feria_partner_id: newPartnerId,
                    });
                    // Update local model so the UI reacts immediately
                    currentTable.feria_partner_id = partner || false;
                    currentTable.feria_partner_name = partner ? partner.name : false;
                }
            }
        }
        return super.setPartnerToCurrentOrder(...arguments);
    },

    /**
     * Override setTableFromUi to auto-assign the partner saved in feria_partner_id
     * to the order when opening a table.
     */
    async setTableFromUi(table, orderUuid = null) {
        await super.setTableFromUi(...arguments);

        // After the table is set, auto-assign the feria partner if present
        const actualTable = table.parent_id ? table.getParent() : table;
        const feriaPartner = actualTable.feria_partner_id;

        if (feriaPartner) {
            const currentOrder = this.getOrder();
            if (currentOrder && !currentOrder.getPartner()) {
                // Use setPartner directly to avoid the duplicate-table check
                // (the partner IS assigned to this table, so it's correct)
                currentOrder.setPartner(feriaPartner);
            }
        }
    },

    /**
     * Open the recharge wizard: a NumberPopup to enter the amount.
     * Then add the recharge product to the current order with that exact price.
     * No discount is applied — the entered amount is the final price.
     */
    async openFeriaRechargeWizard() {
        const order = this.getOrder();
        if (!order) {
            this.notification.add(_t("No hay pedido activo."), { type: "warning" });
            return;
        }

        const rechargeProduct = this.config.feria_recharge_product_id;
        if (!rechargeProduct) {
            this.notification.add(
                _t("No se ha configurado el producto de recarga. Configúrelo en Ajustes del POS."),
                { type: "danger", sticky: true }
            );
            return;
        }

        const amount = await makeAwaitable(this.dialog, NumberPopup, {
            title: _t("Recarga de Monedero"),
            subtitle: _t("Introduzca el importe a recargar"),
            startingValue: "",
            placeholder: _t("0,00"),
            confirmButtonLabel: _t("Aceptar"),
        });

        if (!amount || parseFloat(amount) <= 0) {
            return;
        }

        const rechargeAmount = parseFloat(amount);

        // Get the product template for the recharge product
        const productTmpl = rechargeProduct.product_tmpl_id;

        // Add the recharge product to the order with the entered amount as the final price.
        // We pass discount: 0 and price_type: "manual" to prevent any automatic
        // pricelist recalculation from applying a discount to the recharge line.
        const line = await this.addLineToCurrentOrder(
            {
                product_id: rechargeProduct,
                product_tmpl_id: productTmpl,
                price_unit: rechargeAmount,
                price_type: "manual",
                discount: 0,
                qty: 1,
            },
            {}
        );

        // Force the price and discount after creation to override any automatic recomputation
        if (line) {
            line.price_unit = rechargeAmount;
            line.discount = 0;
            line.price_type = "manual";
        }
    },
});


