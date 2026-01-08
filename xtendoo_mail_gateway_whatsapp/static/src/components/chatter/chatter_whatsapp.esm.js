/** @odoo-module **/

import {Chatter} from "@mail/chatter/web_portal/chatter";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
    },

    async onClickWhatsappTemplate() {
        const thread = this.state.thread;
        if (!thread) {
            return;
        }

        // Get the first phone/mobile field from the partner
        let numberFieldName = "mobile";

        await this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                target: "new",
                name: _t("Send WhatsApp Template"),
                res_model: "whatsapp.composer",
                views: [[false, "form"]],
                context: {
                    default_res_model: thread.model,
                    default_res_id: thread.id,
                    default_number_field_name: numberFieldName,
                },
            },
            {
                onClose: () => {
                    if (thread) {
                        thread.fetchNewMessages();
                    }
                },
            }
        );
    },
});

