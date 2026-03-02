/** @odoo-module */

import { FloorScreen } from "@pos_restaurant/app/screens/floor_screen/floor_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ask } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { onMounted } from "@odoo/owl";

patch(FloorScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            this.feriaEnsureDefaultTables();
        });
    },

    /**
     * Returns the customer name for a given table.
     * Reads from the persistent feria_partner_name field
     * so it survives session close, order finalization, etc.
     */
    getTableCustomerName(table) {
        return table.feria_partner_name || false;
    },

    /**
     * Ensure there are at least 100 tables on the active floor.
     * Creates missing ones in a single batch call.
     */
    async feriaEnsureDefaultTables() {
        const floor = this.activeFloor;
        if (!floor) {
            return;
        }
        const MIN_TABLES = 100;
        const allTables = floor.table_ids?.filter((t) => t.active) || [];
        if (allTables.length >= MIN_TABLES) {
            return;
        }
        const existingNumbers = new Set(allTables.map((t) => t.table_number));
        const tablesToCreate = [];
        for (let i = 1; i <= MIN_TABLES; i++) {
            if (!existingNumbers.has(i)) {
                tablesToCreate.push({
                    active: true,
                    table_number: i,
                    position_v: 0,
                    position_h: 0,
                    width: 100,
                    height: 100,
                    shape: "square",
                    seats: 2,
                    color: "rgb(53, 211, 116)",
                    floor_id: floor.id,
                });
            }
        }
        if (tablesToCreate.length > 0) {
            // Create in batches of 20 to avoid timeout
            for (let i = 0; i < tablesToCreate.length; i += 20) {
                const batch = tablesToCreate.slice(i, i + 20);
                await this.pos.data.create("restaurant.table", batch);
            }
        }
    },

    /**
     * Add a single table with the next available number.
     */
    async onFeriaAddTable() {
        if (!this.activeFloor) {
            return;
        }
        const nextNumber = this._getNewTableNumber();
        await this.pos.data.create("restaurant.table", [{
            active: true,
            table_number: nextNumber,
            position_v: 0,
            position_h: 0,
            width: 100,
            height: 100,
            shape: "square",
            seats: 2,
            color: "rgb(53, 211, 116)",
            floor_id: this.activeFloor.id,
        }]);
    },

    /**
     * Remove the last table (highest table_number).
     * If it has a customer assigned, ask for confirmation first.
     * Otherwise delete directly without asking.
     */
    async onFeriaRemoveLastTable() {
        if (!this.activeFloor) {
            return;
        }
        const tables = this.activeTables.sort((a, b) => a.table_number - b.table_number);
        if (tables.length === 0) {
            return;
        }
        const lastTable = tables[tables.length - 1];
        const customerName = this.getTableCustomerName(lastTable);

        // Only ask confirmation if the table has a customer assigned
        if (customerName) {
            const confirmed = await ask(this.dialog, {
                title: _t("Mesa %s - %s", lastTable.table_number, customerName),
                body: _t("Esta mesa tiene el cliente '%s' asignado. ¿Eliminar de todos modos?", customerName),
            });
            if (!confirmed) {
                return;
            }
        }

        try {
            const response = await this.pos.data.call(
                "restaurant.table",
                "are_orders_still_in_draft",
                [[lastTable.id]]
            );
            if (response) {
                // Clear the persistent customer assignment
                if (lastTable.feria_partner_id) {
                    this.pos.data.write("restaurant.table", [lastTable.id], {
                        feria_partner_id: false,
                    });
                }
                // Remove any open orders on that table first
                for (const order of this.pos.getOpenOrders()) {
                    if (order.table_id?.id === lastTable.id) {
                        this.pos.removeOrder(order, false);
                    }
                }
                const records = this.pos.data.write("restaurant.table", [lastTable.id], {
                    active: false,
                });
                records[0].delete();
            }
        } catch {
            // silently fail
        }
    },
});
