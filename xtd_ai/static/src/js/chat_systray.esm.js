import {Component, onWillStart, useState} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {userHasAiGroup} from "./chat_service.esm";
import {ChatLogo} from "./chat_conversation.esm";

/** Compact systray icon (like the other systray items) that toggles the window. */
export class ChatSystray extends Component {
    static template = "xtd_ai.Systray";
    static components = {ChatLogo};
    static props = {};

    setup() {
        this.chat = useService("xtd_ai.chat");
        this.state = useState(this.chat.state);
        this.ui = useState({visible: false});
        onWillStart(async () => {
            this.ui.visible = await userHasAiGroup();
        });
    }

    get label() {
        return _t("Asistente IA");
    }
}

registry
    .category("systray")
    .add("xtd_ai.systray", {Component: ChatSystray}, {sequence: 15});
