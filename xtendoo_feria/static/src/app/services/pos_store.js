/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    /**
     * Override to check if the partner is already assigned to another table.
     * In a feria context, each customer should only be at one table.
     */
    setPartnerToCurrentOrder(partner) {
        if (partner && this.config.module_pos_restaurant) {
            const currentOrder = this.getOrder();
            const currentTableId = currentOrder?.table_id?.id;

            const allOrders = this.models["pos.order"].getAll();
            for (const order of allOrders) {
                if (order.finalized || !order.table_id) {
                    continue;
                }
                if (order.table_id.id === currentTableId) {
                    continue;
                }
                const orderPartner = order.getPartner();
                if (orderPartner && orderPartner.id === partner.id) {
                    this.notification.add(
                        _t("'%s' ya está en la Mesa %s", partner.name, order.table_id.table_number),
                        { type: "danger", sticky: true }
                    );
                    return;
                }
            }
        }
        return super.setPartnerToCurrentOrder(...arguments);
    },
});
