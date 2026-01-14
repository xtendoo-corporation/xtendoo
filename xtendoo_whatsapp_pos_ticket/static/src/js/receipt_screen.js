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
            // Obtener el HTML del ticket generado en el frontend
            const ticketHtml = this.el.querySelector('.pos-receipt')?.outerHTML;
            if (!ticketHtml) {
                this.notification.add(_t("No se pudo obtener el HTML del ticket para enviar por WhatsApp."), {
                    type: "danger",
                });
                this.whatsappState.sending = false;
                return;
            }
            const result = await this.orm.call(
                "pos.order",
                "send_whatsapp_ticket_html",
                [order.id, true, ticketHtml]
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
