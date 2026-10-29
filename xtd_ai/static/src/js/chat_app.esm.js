import {Component, onWillStart, useState} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {deserializeDateTime} from "@web/core/l10n/dates";
import {
    ChatConversation,
    ChatLogo,
    ChatMenu,
    formatChatDate,
} from "./chat_conversation.esm";

/** "14:05" for today, "20/10" otherwise. */
export function formatShortDate(value) {
    try {
        const date = deserializeDateTime(value);
        const now = luxon.DateTime.now();
        return date.hasSame(now, "day")
            ? date.toLocaleString({hour: "2-digit", minute: "2-digit"})
            : date.toLocaleString({day: "2-digit", month: "2-digit"});
    } catch {
        return "";
    }
}

/**
 * Full-page client action: conversation list (search, new) on the left, the
 * conversation in the centre. Past conversations open read-only.
 */
export class ChatApp extends Component {
    static template = "xtd_ai.ChatApp";
    static components = {ChatConversation, ChatLogo, ChatMenu};
    static props = ["*"];

    setup() {
        this.chat = useService("xtd_ai.chat");
        this.ui = useService("ui");
        this.state = useState(this.chat.state);
        this.view = useState({sidebar: !this.ui.isSmall, search: ""});
        onWillStart(async () => {
            // The floating window is redundant while the app is on screen
            this.chat.close();
            const wanted = this.props.action?.params?.conversation_id || null;
            await this.chat.openApp(wanted);
        });
    }

    get conversations() {
        const term = this.view.search.trim().toLowerCase();
        if (!term) {
            return this.state.conversations;
        }
        return this.state.conversations.filter((c) =>
            c.name.toLowerCase().includes(term)
        );
    }

    formatDate(value) {
        return formatChatDate(value);
    }

    shortDate(value) {
        return formatShortDate(value);
    }

    toggleSidebar() {
        this.view.sidebar = !this.view.sidebar;
    }

    async onSelect(conversation) {
        if (conversation.state === "open") {
            await this.chat.showCurrent();
        } else {
            await this.chat.selectConversation(conversation.id);
        }
        if (this.ui.isSmall) {
            this.view.sidebar = false;
        }
    }

    async onNew() {
        await this.chat.newConversation();
        if (this.ui.isSmall) {
            this.view.sidebar = false;
        }
    }
}

registry.category("actions").add("xtd_ai.app", ChatApp);
