/** @odoo-module */

import { CashMovePopup } from "@point_of_sale/app/navbar/cash_move_popup/cash_move_popup";
import { MoneyDetailsPopup } from "@point_of_sale/app/utils/money_details_popup/money_details_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(CashMovePopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.moneyDetails = null;
    },

    async openDetailsPopup() {
        const action = this.state.type === "in" ? _t("Cash in") : _t("Cash out");
        this.hardwareProxy.openCashbox(action);
        this.dialog.add(MoneyDetailsPopup, {
            moneyDetails: this.moneyDetails,
            action: action,
            getPayload: (payload) => {
                const { total, moneyDetailsNotes, moneyDetails } = payload;
                this.state.amount = this.env.utils.formatCurrency(total, false);
                if (moneyDetailsNotes) {
                    // Si ya hay una razón, agregar las notas de detalles
                    if (this.state.reason) {
                        this.state.reason += "\n" + moneyDetailsNotes;
                    } else {
                        this.state.reason = moneyDetailsNotes;
                    }
                }
                this.moneyDetails = moneyDetails;
            },
            context: this.state.type === "in" ? "Cash in" : "Cash out",
        });
    },

    onAmountChange() {
        // Si se cambia manualmente el monto, limpiar los detalles
        if (this.moneyDetails) {
            this.moneyDetails = null;
        }
    },
});

