import {Message} from "@mail/core/common/message_model";
import {patch} from "@web/core/utils/patch";
import {url} from "@web/core/utils/urls";
import {router} from "@web/core/browser/router";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.gateway_thread_data = {};
    },
    get resUrl() {
        if (!this.gateway_thread_data || !this.gateway_thread_data.model) {
            return super.resUrl;
        }
        return url(
            router.stateToUrl({
                model: this.gateway_thread_data.model,
                resId: this.gateway_thread_data.id,
            })
        );
    },
    get editable() {
        return super.editable && !this.gateway_type;
    },
});
