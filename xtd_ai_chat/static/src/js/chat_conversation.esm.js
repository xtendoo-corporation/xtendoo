import {Component, useEffect, useExternalListener, useRef, useState} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {deserializeDateTime} from "@web/core/l10n/dates";
import {parseSafeMarkdown} from "./safe_markdown.esm";
import {ACCEPT, MAX_FILES, fileIcon, formatSize} from "./chat_service.esm";

/** Renders parsed markdown blocks using only t-esc (no HTML injection path). */
export class SafeText extends Component {
    static template = "xtd_ai_chat.SafeText";
    static props = {text: {type: String, optional: true}};

    get blocks() {
        return parseSafeMarkdown(this.props.text || "");
    }
}

export function formatChatDate(value) {
    try {
        return deserializeDateTime(value).toLocaleString({
            hour: "2-digit",
            minute: "2-digit",
            day: "2-digit",
            month: "2-digit",
        });
    } catch {
        return "";
    }
}

/** Small own logo (inline SVG in the templates): a chat bubble with a sparkle. */
export class ChatLogo extends Component {
    static template = "xtd_ai_chat.Logo";
    static props = {size: {type: Number, optional: true}};
}

/** "⋯" menu: confirmation toggle (+ optionally "new conversation"). */
export class ChatMenu extends Component {
    static template = "xtd_ai_chat.Menu";
    static props = {showNew: {type: Boolean, optional: true}};

    setup() {
        this.chat = useService("xtd_ai_chat");
        this.state = useState(this.chat.state);
        this.ui = useState({open: false});
        this.root = useRef("root");
        useExternalListener(window, "click", (ev) => {
            if (this.ui.open && this.root.el && !this.root.el.contains(ev.target)) {
                this.ui.open = false;
            }
        });
    }

    get confirmHelp() {
        return this.state.settings.forced
            ? _t("Tu administrador exige confirmación para todas las acciones.")
            : "";
    }

    toggle() {
        this.ui.open = !this.ui.open;
    }

    onToggleConfirm(ev) {
        this.chat.setConfirmWrites(ev.target.checked);
    }

    async onNew() {
        this.ui.open = false;
        await this.chat.newConversation();
    }
}

/**
 * Messages, empty state with suggestion chips, confirmation cards and the input bar
 * of the conversation held by the chat service. Shared by the floating window and the
 * app. A closed conversation is read-only: no input, no actionable cards.
 */
export class ChatConversation extends Component {
    static template = "xtd_ai_chat.ChatConversation";
    static components = {SafeText, ChatLogo};
    static props = {};

    setup() {
        this.chat = useService("xtd_ai_chat");
        this.state = useState(this.chat.state);
        this.listRef = useRef("list");
        this.inputRef = useRef("input");
        this.fileRef = useRef("file");
        this.accept = ACCEPT;
        useEffect(
            () => {
                const el = this.listRef.el;
                if (el) {
                    el.scrollTop = el.scrollHeight;
                }
            },
            () => [this.state.messages.length, this.state.runningRunId]
        );
        useEffect(
            () => this.autoGrow(),
            () => [this.state.draft]
        );
    }

    get isReadOnly() {
        return this.state.conversationState !== "open";
    }

    get showEmpty() {
        return !this.state.loading && !this.state.messages.length;
    }

    get uploading() {
        return this.state.attachments.some((a) => a.uploading);
    }

    get canSend() {
        return (
            !this.isReadOnly &&
            (Boolean(this.state.draft.trim()) ||
                this.state.attachments.some((a) => a.id)) &&
            !this.uploading &&
            !this.state.runningRunId &&
            !this.state.busy
        );
    }

    get canAttach() {
        return (
            !this.isReadOnly &&
            !this.state.busy &&
            this.state.attachments.length < MAX_FILES
        );
    }

    get showBanner() {
        return Boolean(this.state.banner) && !this.isReadOnly;
    }

    formatDate(value) {
        return formatChatDate(value);
    }

    fileIcon(mimetype) {
        return fileIcon(mimetype);
    }

    fileSize(bytes) {
        return formatSize(bytes);
    }

    autoGrow() {
        const el = this.inputRef.el;
        if (el) {
            el.style.height = "auto";
            el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
        }
    }

    actionStateLabel(action) {
        if (action.state === "pending" && !action.actionable) {
            return _t("Pendiente (conversación cerrada, ya no se puede confirmar)");
        }
        return {
            pending: _t("Pendiente"),
            confirmed: _t("Hecho"),
            cancelled: _t("Cancelada"),
            expired: _t("Caducada"),
            failed: _t("Fallida"),
        }[action.state];
    }

    async onSend() {
        if (!this.canSend) {
            return;
        }
        try {
            await this.chat.send();
        } catch {
            // The service restored the draft and the attachments; the error is shown
        } finally {
            this.syncInput();
        }
    }

    /**
     * Mirror the draft into the textarea. t-model alone is not enough when the
     * draft is cleared in the same frame it was typed (fast typing or paste then
     * Enter): Owl never rendered the typed value, sees no change and leaves the
     * old text in the box.
     */
    syncInput() {
        const el = this.inputRef.el;
        if (el && el.value !== this.state.draft) {
            el.value = this.state.draft;
            this.autoGrow();
        }
    }

    async onChip(chip) {
        if (this.isReadOnly) {
            return;
        }
        if (chip.send) {
            try {
                await this.chat.send(chip.text);
            } catch {
                // Error already shown by the service
            }
            return;
        }
        this.state.draft = chip.text;
        if (chip.attach && this.fileRef.el) {
            this.fileRef.el.click();
        } else if (this.inputRef.el) {
            this.inputRef.el.focus();
        }
    }

    /**
     * Record links open inside the web client (no reload), so the chat window
     * stays. Ctrl/Cmd/Shift+click keep the browser default (new tab or window).
     */
    onRecordClick(ev, resModel, resId) {
        if (ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.button !== 0) {
            return;
        }
        if (!resModel || !resId) {
            return;
        }
        ev.preventDefault();
        this.chat.openRecord(resModel, resId);
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) {
            ev.preventDefault();
            this.onSend();
        }
    }

    onAttachClick() {
        if (this.canAttach && this.fileRef.el) {
            this.fileRef.el.click();
        }
    }

    async onFilesSelected(ev) {
        const files = Array.from(ev.target.files || []);
        ev.target.value = "";
        await this.chat.addFiles(files);
    }
}
