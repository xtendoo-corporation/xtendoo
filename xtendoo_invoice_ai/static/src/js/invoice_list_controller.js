/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
    },

    /**
     * Determinar si mostrar el botón OCR
     */
    get showOCRButton() {
        return this.props.resModel === "account.move" &&
               (this.props.context?.default_move_type === "in_invoice" ||
                this.props.context?.move_type === "in_invoice");
    },

    /**
     * Abrir selector de archivos para OCR
     */
    async onClickOCRButton() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.pdf,.png,.jpg,.jpeg';
        input.multiple = true;

        input.onchange = async (e) => {
            const files = Array.from(e.target.files);
            if (files.length === 0) return;

            await this.processFilesWithOCR(files);
        };

        input.click();
    },

    /**
     * Procesar archivos con OCR
     */
    async processFilesWithOCR(files) {
        const attachmentIds = [];

        // Mostrar notificación de proceso
        this.notification.add(
            `Subiendo ${files.length} archivo(s)...`,
            { type: "info" }
        );

        for (const file of files) {
            try {
                // Leer archivo como base64
                const fileData = await this.readFileAsBase64(file);

                // Crear adjunto temporal
                const attId = await this.orm.create("ir.attachment", [{
                    name: file.name,
                    datas: fileData,
                    mimetype: file.type,
                }]);

                // El create devuelve un array con un ID, tomamos el primer elemento
                if (Array.isArray(attId) && attId.length > 0) {
                    attachmentIds.push(attId[0]);
                } else if (typeof attId === 'number') {
                    attachmentIds.push(attId);
                }
            } catch (error) {
                console.error(`Error processing file ${file.name}:`, error);
                this.notification.add(
                    `Error al subir archivo: ${file.name}`,
                    { type: "danger" }
                );
            }
        }

        if (attachmentIds.length > 0) {
            // Mostrar notificación de procesamiento
            this.notification.add(
                `Procesando ${attachmentIds.length} factura(s) con IA...`,
                { type: "info" }
            );

            // Llamar al wizard para procesar los adjuntos
            try {
                const action = await this.orm.call(
                    "xtendoo.invoice.ai.wizard",
                    "create_and_process_attachments",
                    [attachmentIds],  // Pasar como lista de IDs
                    {}
                );

                if (action) {
                    this.action.doAction(action);
                } else {
                    this.notification.add(
                        "Facturas procesadas correctamente",
                        { type: "success" }
                    );
                    // Recargar la vista
                    await this.model.root.load();
                    this.render();
                }
            } catch (error) {
                console.error("Error processing invoices:", error);
                const errorMsg = error.data?.message || error.message || "Error al procesar las facturas con IA";
                this.notification.add(errorMsg, { type: "danger", sticky: true });
            }
        } else {
            this.notification.add(
                "No se pudieron subir los archivos",
                { type: "warning" }
            );
        }
    },

    /**
     * Leer archivo como base64
     */
    readFileAsBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                // Eliminar el prefijo "data:...;base64," del resultado
                const base64 = reader.result.split(',')[1];
                resolve(base64);
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    },
});
