/** @odoo-module **/

import { registry } from "@web/core/registry";
import { InvoiceAIUploader } from "./invoice_ai_uploader";

export class InvoiceAIUploadButton extends InvoiceAIUploader {
    static template = "xtendoo_invoice_ai.InvoiceAIUploadButton";
}

registry.category("view_widgets").add("invoice_ai_upload_button", {
    component: InvoiceAIUploadButton,
});

