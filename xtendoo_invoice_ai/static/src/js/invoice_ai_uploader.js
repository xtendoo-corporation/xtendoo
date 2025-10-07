/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { FileUploader } from "@web/views/fields/file_handler";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component, markup } from "@odoo/owl";

export class InvoiceAIUploader extends Component {
    static template = "xtendoo_invoice_ai.InvoiceAIUploader";
    static components = {
        FileUploader,
    };
    static props = {
        ...standardWidgetProps,
        record: { type: Object, optional: true },
        slots: { type: Object, optional: true },
        resModel: { type: String, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.attachmentIdsToProcess = [];
    }

    get acceptedFileExtensions() {
        return ".pdf,.png,.jpg,.jpeg";
    }

    async onFileUploaded(file) {
        const att_data = {
            name: file.name,
            mimetype: file.type,
            datas: file.data,
        };
        // Limpiar el contexto para asegurar que la llamada `create` no falle por `default_*` desconocidos
        const cleanContext = Object.fromEntries(
            Object.entries(this.env.searchModel?.context || {}).filter(
                ([key]) => !key.startsWith('default_')
            )
        );
        const [att_id] = await this.orm.create("ir.attachment", [att_data], {
            context: cleanContext
        });
        this.attachmentIdsToProcess.push(att_id);
    }

    async onUploadComplete() {
        if (this.attachmentIdsToProcess.length === 0) {
            return;
        }

        try {
            // Abrir el wizard de importación con los adjuntos
            const action = await this.orm.call(
                "xtendoo.invoice.ai.wizard",
                "create_and_process_attachments",
                [this.attachmentIdsToProcess],
                {
                    context: {
                        ...this.env.searchModel?.context,
                        default_create_partner_if_missing: true,
                        default_attach_original: true,
                    }
                }
            );

            if (action.context && action.context.notifications) {
                for (const [file, msg] of Object.entries(action.context.notifications)) {
                    this.notification.add(msg, {
                        title: file,
                        type: "info",
                        sticky: true,
                    });
                }
                delete action.context.notifications;
            }

            if (action.help?.length) {
                action.help = markup(action.help);
            }

            this.action.doAction(action);
        } finally {
            // Asegurarse de que los adjuntos se limpien en caso de éxito o error
            this.attachmentIdsToProcess = [];
        }
    }
}

