/** @odoo-module */

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
    /**
     * Open WhatsApp composer wizard for the current record
     */
    sendWhatsapp() {
        const send = async (thread) => {
            // Determine the phone field to use based on model
            let numberFieldName = "mobile";

            // Check if the model has specific phone fields
            if (thread.model === "res.partner") {
                numberFieldName = "mobile";
            } else if ("partner_id" in (thread.record || {})) {
                numberFieldName = "partner_id.mobile";
            }

            // Try to get available gateways
            const gateways = await this.env.services.orm.searchRead(
                "mail.gateway",
                [["gateway_type", "=", "whatsapp"]],
                ["id", "name"],
                { limit: 1 }
            );

            if (!gateways || gateways.length === 0) {
                this.env.services.notification.add(
                    _t("No WhatsApp gateway configured"),
                    { type: "warning" }
                );
                return;
            }

            await new Promise((resolve) => {
                this.env.services.action.doAction(
                    {
                        type: "ir.actions.act_window",
                        name: _t("Send WhatsApp Message"),
                        res_model: "whatsapp.composer",
                        view_mode: "form",
                        views: [[false, "form"]],
                        target: "new",
                        context: {
                            default_res_model: thread.model,
                            default_res_id: thread.id,
                            default_number_field_name: numberFieldName,
                            default_gateway_id: gateways[0].id,
                            default_find_gateway: false,
                        },
                    },
                    { onClose: resolve }
                );
            });

            // Refresh messages after sending
            this.store.Thread.insert({
                model: this.props.threadModel,
                id: this.props.threadId,
            }).fetchNewMessages();
        };

        if (this.state.thread.id) {
            send(this.state.thread);
        } else {
            // If record not saved yet, save first
            this.onThreadCreated = send;
            this.props.saveRecord?.();
        }
    },
});

