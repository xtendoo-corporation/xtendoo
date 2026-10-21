import { Message } from "@mail/core/common/message_model";
import { patch } from "@web/core/utils/patch";

// OCA mail_gateway_whatsapp (PR #203, 19.0) usa en su plantilla `message.notifications.length`, pero en este
// core de 19 el campo de la relación se llama `notification_ids`: `message.notifications` es undefined y
// al leer `.length` falla el render de CADA mensaje de WhatsApp (el hilo queda vacío).
// Mientras el PR no lo corrija, se expone `notifications` como alias de `notification_ids`.
patch(Message.prototype, {
    get notifications() {
        return this.notification_ids;
    },
});
