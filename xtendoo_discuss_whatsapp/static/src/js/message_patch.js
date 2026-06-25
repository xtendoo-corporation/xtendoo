/** @odoo-module **/

import { Message } from "@mail/core/common/message";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    get isAlignedRight() {
        return Boolean(
            this.props.message.isSelfAuthored &&
                (this.env.inChatWindow || this.env.inDiscussApp)
        );
    },

    get attClass() {
        return {
            ...super.attClass,
            "o-xtd-wa-self":
                this.props.message.isSelfAuthored &&
                (this.env.inChatWindow || this.env.inDiscussApp),
        };
    },
});
