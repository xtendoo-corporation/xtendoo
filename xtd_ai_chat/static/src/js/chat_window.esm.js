import {Component, useState} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {ChatConversation, ChatLogo, ChatMenu, SafeText} from "./chat_conversation.esm";

export {SafeText};

/**
 * Floating chat window anchored bottom-right (opened from the systray icon).
 * States: closed / open / minimised (only the header bar). Always shows the current
 * conversation unless a past one is being read (read-only).
 */
export class ChatWindow extends Component {
    static template = "xtd_ai_chat.ChatWindow";
    static components = {ChatConversation, ChatLogo, ChatMenu};
    static props = {};

    setup() {
        this.chat = useService("xtd_ai_chat");
        this.action = useService("action");
        this.state = useState(this.chat.state);
    }

    get title() {
        return _t("Asistente IA");
    }

    /** Full-page app with the same conversation. */
    async onExpand() {
        const id = this.state.conversationId;
        this.chat.close();
        await this.action.doAction({
            type: "ir.actions.client",
            tag: "xtd_ai_chat.app",
            target: "current",
            params: {conversation_id: id},
        });
    }
}

/** Mounted once in the web client (main components): visible only while open. */
export class ChatWindowHost extends Component {
    static template = "xtd_ai_chat.ChatWindowHost";
    static components = {ChatWindow};
    static props = {};

    setup() {
        this.chat = useService("xtd_ai_chat");
        this.state = useState(this.chat.state);
    }
}

registry
    .category("main_components")
    .add("xtd_ai_chat.window", {Component: ChatWindowHost});
