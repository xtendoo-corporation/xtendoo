/** @odoo-module **/

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.whatsappState = useState({
            sending: false,
            sent: false,
            error: null,
        });
    },

    get isWhatsappEnabled() {
        return this.pos.config.whatsapp_ticket_enabled;
    },

    get partnerHasPhone() {
        const partner = this.currentOrder.get_partner();
        return partner && (partner.mobile || partner.phone);
    },

    get partnerPhone() {
        const partner = this.currentOrder.get_partner();
        if (!partner) return null;
        return partner.mobile || partner.phone;
    },

    get canSendWhatsapp() {
        const partner = this.currentOrder.get_partner();
        return this.isWhatsappEnabled && partner && this.partnerHasPhone;
    },

    async sendWhatsappTicket() {
        const order = this.currentOrder;
        const partner = order.get_partner();

        if (!partner) {
            this.notification.add(_t("Por favor, seleccione un cliente para enviar el ticket por WhatsApp."), {
                type: "warning",
            });
            return;
        }

        if (!this.partnerHasPhone) {
            this.notification.add(_t("El cliente %s no tiene número de teléfono configurado.", partner.name), {
                type: "danger",
            });
            return;
        }

        if (typeof order.id !== "number") {
            this.notification.add(_t("El pedido no está sincronizado. Por favor, espere e intente de nuevo."), {
                type: "warning",
            });
            return;
        }

        this.whatsappState.sending = true;
        this.whatsappState.error = null;

        try {
            // Obtener el HTML del ticket generado en frontend
            const receiptElement = document.querySelector('.pos-receipt-container');
            let ticket_html = '';
            if (receiptElement) {
                ticket_html = receiptElement.innerHTML;
            }

            // Obtener el logo de la compañía si existe
            let logo_html = '';
            const logoImg = document.querySelector('.pos-receipt-logo img, .pos-company-logo img');
            if (logoImg && logoImg.src) {
                logo_html = `<div style='text-align:center;margin-bottom:8px;'><img src='${logoImg.src}' style='max-width:120px;max-height:60px;'/></div>`;
            }

            // Obtener los estilos CSS aplicados al ticket
            let ticket_css = '';
            document.querySelectorAll('style').forEach(style => {
                ticket_css += style.innerHTML + '\n';
            });
            document.querySelectorAll('link[rel="stylesheet"]').forEach(link => {
                ticket_css += `@import url('${link.href}');\n`;
            });

            // CSS específico para formato de ticket térmico
            const thermal_css = `
                body { background: #fff !important; color: #000 !important; }
                .pos-receipt-container { background: #fff !important; color: #000 !important; max-width: 300px; margin: 0 auto; font-size: 13px; }
                .pos-receipt-logo, .pos-company-logo { text-align: center; margin-bottom: 8px; }
                img { display: block; margin: 0 auto; }
            `;

            // Construir el HTML completo para el PDF
            const full_html = `
                <html>
                <head>
                    <meta charset='utf-8'/>
                    <style>
                        ${thermal_css}
                        ${ticket_css}
                    </style>
                </head>
                <body>
                    ${logo_html}
                    <div class="pos-receipt-container">
                        ${ticket_html}
                    </div>
                </body>
                </html>
            `;

            // Llamada al backend para enviar el ticket HTML completo por WhatsApp
            const result = await this.orm.call(
                "pos.order",
                "send_whatsapp_ticket_html",
                [order.id, true, full_html, '']
            );

            if (result.success) {
                this.whatsappState.sent = true;
                this.notification.add(_t("Ticket enviado correctamente por WhatsApp"), {
                    type: "success",
                });
            } else {
                this.whatsappState.error = result.error;
                this.notification.add(result.error || _t("Error al enviar el ticket por WhatsApp"), {
                    type: "danger",
                });
            }
        } catch (error) {
            console.error("Error sending WhatsApp ticket:", error);
            this.whatsappState.error = error.message;
            this.notification.add(_t("Error al enviar el ticket por WhatsApp: %s", error.message), {
                type: "danger",
            });
        } finally {
            this.whatsappState.sending = false;
        }
    },
});
