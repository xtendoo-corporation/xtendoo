/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { InvoiceAIUploader } from "./invoice_ai_uploader";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
    },

    /**
     * Verificar si estamos en la vista de facturas de proveedor
     */
    get isVendorBillList() {
        return this.props.resModel === "account.move" &&
               (this.props.context?.default_move_type === "in_invoice" ||
                this.props.context?.move_type === "in_invoice");
    },

    /**
     * Abrir wizard de importación con IA
     */
    async onImportWithAI() {
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "xtendoo.invoice.ai.wizard",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_create_partner_if_missing: true,
                default_attach_original: true,
            },
        });
    },
});

// Registrar el componente InvoiceAIUploader
export { InvoiceAIUploader };
