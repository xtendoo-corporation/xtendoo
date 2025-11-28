/**
 * Extiende el componente Chatter para añadir el botón WhatsApp que llama al método Python.
 */
import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/components/chatter/chatter";
import { useService } from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    async sendWhatsapp() {
        const thread = this.props.thread;
        let numberFieldName = "mobile";
        if (thread.model === "res.partner") {
            numberFieldName = "mobile";
        } else if ("partner_id" in (thread.record || {})) {
            numberFieldName = "partner_id.mobile";
        }
        // Comprobar si hay gateway de WhatsApp
        const orm = this.env.services.orm;
        const notification = this.env.services.notification;
        const gateways = await orm.searchRead(
            "mail.gateway",
            [["gateway_type", "=", "whatsapp"]],
            ["id", "name"],
            { limit: 1 }
        );
        if (!gateways || gateways.length === 0) {
            notification.add(
                "No WhatsApp gateway configured",
                { type: "warning" }
            );
            return;
        }
        this.env.services.action.doAction({
            type: "ir.actions.act_window",
            name: "Send WhatsApp Message",
            res_model: "whatsapp.composer",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_res_model: thread.model,
                default_res_id: thread.id,
                default_number_field_name: numberFieldName,
            },
        });
    },
});
