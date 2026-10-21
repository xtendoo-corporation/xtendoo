import {reactive} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {rpc} from "@web/core/network/rpc";
import {user} from "@web/core/user";
import {_t} from "@web/core/l10n/translation";
import {browser} from "@web/core/browser/browser";

export const XTD_AI_GROUP = "xtd_ai_gateway.group_xtd_ai_user";
export const MAX_FILE_BYTES = 10 * 1024 * 1024;
export const MAX_FILES = 5;
export const ALLOWED_TYPES = [
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
];
export const ACCEPT =
    ".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/png,image/jpeg,image/webp";

export function formatSize(bytes) {
    bytes = Number(bytes) || 0;
    if (bytes < 1024) {
        return `${bytes} B`;
    }
    if (bytes < 1024 * 1024) {
        return `${Math.round(bytes / 1024)} KB`;
    }
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function fileIcon(mimetype) {
    if (mimetype === "application/pdf") {
        return "fa-file-pdf-o";
    }
    if ((mimetype || "").startsWith("image/")) {
        return "fa-file-image-o";
    }
    return "fa-file-o";
}

export const xtdAiChatService = {
    dependencies: ["bus_service", "action", "ui"],
    start(env, {bus_service, action: actionService, ui}) {
        const state = reactive({
            isOpen: false,
            minimized: false,
            banner: null, // {previousId} while the "new conversation" notice is shown
            suggestions: [],
            draft: "",
            attachments: [], // [{key, id?, name, mimetype, size, uploading, error?}]
            currentId: null, // The open (writable) conversation
            loading: false,
            busy: false,
            conversationId: null,
            conversationState: "open",
            messages: [],
            conversations: [],
            runningRunId: null,
            settings: {forced: false, confirm_writes: true},
            error: null,
        });
        let reloadSeq = 0;

        // Window state survives page reloads (F5) within the same browser tab.
        // Per-viewer convenience only: wrapped, and the chat works without it.
        const STORAGE_KEY = "xtd_ai_chat.window";
        const saveWindow = () => {
            try {
                sessionStorage.setItem(
                    STORAGE_KEY,
                    JSON.stringify({isOpen: state.isOpen, minimized: state.minimized})
                );
            } catch {
                // Storage unavailable (private mode, blocked): nothing to remember
            }
        };
        const loadWindow = () => {
            try {
                return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "null");
            } catch {
                return null;
            }
        };

        const call = async (route, params = {}) => {
            try {
                state.error = null;
                return await rpc(route, params);
            } catch (error) {
                state.error = error?.data?.message || error?.message || String(error);
                throw error;
            }
        };

        const service = {
            state,
            async ensureConversation(forceNew = false, fresh = false) {
                const res = await call("/xtd_ai/chat/open", {new: forceNew, fresh});
                state.conversationId = res.conversation_id;
                state.currentId = res.conversation_id;
                state.settings = res.settings;
                state.suggestions = res.suggestions || [];
                if (forceNew) {
                    state.banner = null;
                } else if (res.auto_started && res.previous_conversation_id) {
                    state.banner = {previousId: res.previous_conversation_id};
                }
                return res;
            },
            async reload() {
                if (!state.conversationId) {
                    return;
                }
                const seq = ++reloadSeq;
                const res = await call("/xtd_ai/chat/messages", {
                    conversation_id: state.conversationId,
                });
                if (seq !== reloadSeq || res.conversation_id !== state.conversationId) {
                    return; // A newer reload or another conversation superseded this one
                }
                state.messages = res.messages;
                state.conversationState = res.state;
                state.runningRunId = res.running_run_id;
            },
            /** Past conversations of the user (read-only history). */
            async loadHistory() {
                state.conversations = await call("/xtd_ai/chat/conversations", {
                    limit: 50,
                });
            },
            /** Show the current open conversation (creating it if needed). */
            async showCurrent() {
                state.loading = true;
                try {
                    state.messages = [];
                    state.runningRunId = null;
                    await service.ensureConversation();
                    await service.reload();
                } finally {
                    state.loading = false;
                }
            },
            /** Read a past (closed) conversation. It can never be written to. */
            async selectConversation(id) {
                state.loading = true;
                try {
                    state.messages = [];
                    state.runningRunId = null;
                    state.conversationId = id;
                    state.attachments = [];
                    await service.reload();
                } finally {
                    state.loading = false;
                }
            },
            /** Open the app, optionally on a given conversation (e.g. from the window). */
            async openApp(conversationId = null) {
                await service.showCurrent();
                if (conversationId && conversationId !== state.currentId) {
                    await service.selectConversation(conversationId);
                }
                await service.loadHistory();
            },
            dismissBanner() {
                state.banner = null;
            },
            async viewPrevious() {
                const id = state.banner?.previousId;
                if (id) {
                    await service.selectConversation(id);
                }
            },
            async backToCurrent() {
                await service.showCurrent();
            },
            /** Opened from the navbar icon: start a new conversation (see /open). */
            async open() {
                state.isOpen = true;
                state.minimized = false;
                saveWindow();
                state.loading = true;
                state.messages = [];
                state.runningRunId = null;
                state.draft = "";
                state.attachments = [];
                try {
                    await service.ensureConversation(false, true);
                    await service.reload();
                } finally {
                    state.loading = false;
                }
            },
            close() {
                state.isOpen = false;
                saveWindow();
            },
            /** Reopen the window after a page reload, on the same open conversation. */
            async restore() {
                const saved = loadWindow();
                if (!saved || !saved.isOpen) {
                    return;
                }
                state.isOpen = true;
                state.minimized = Boolean(saved.minimized);
                state.loading = true;
                try {
                    await service.ensureConversation();
                    await service.reload();
                } finally {
                    state.loading = false;
                }
            },
            /**
             * Open a record from the chat without reloading the page, so the floating
             * window (a main component) stays open with the same conversation. From
             * the full-page app the conversation moves to the floating window.
             */
            async openRecord(resModel, resId) {
                if (!state.isOpen) {
                    state.isOpen = true;
                    state.minimized = false;
                }
                if (ui.isSmall) {
                    // On phones the window covers the screen: let the record show
                    state.minimized = true;
                }
                saveWindow();
                await actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: resModel,
                    res_id: resId,
                    views: [[false, "form"]],
                    target: "current",
                });
            },
            toggle() {
                return state.isOpen ? service.close() : service.open();
            },
            toggleMinimize() {
                state.minimized = !state.minimized;
                saveWindow();
            },
            async newConversation() {
                state.messages = [];
                state.runningRunId = null;
                state.draft = "";
                state.attachments = [];
                await service.ensureConversation(true);
                await service.reload();
                if (state.conversations.length) {
                    await service.loadHistory();
                }
            },
            /** Validate and upload files for the next message (current open conversation). */
            async addFiles(files) {
                if (state.conversationState !== "open") {
                    return;
                }
                for (const file of Array.from(files || [])) {
                    const entry = {
                        key: `${Date.now()}-${Math.random()}`,
                        name: file.name,
                        mimetype: file.type,
                        size: file.size,
                        uploading: false,
                        id: null,
                        error: null,
                    };
                    const lower = (file.name || "").toLowerCase();
                    const extOk = [".pdf", ".png", ".jpg", ".jpeg", ".webp"].some((e) =>
                        lower.endsWith(e)
                    );
                    if (state.attachments.length >= MAX_FILES) {
                        state.error = _t("Máximo %s adjuntos por mensaje.", MAX_FILES);
                        break;
                    }
                    if (!extOk || (file.type && !ALLOWED_TYPES.includes(file.type))) {
                        state.error = _t(
                            "«%s»: tipo no admitido. Solo PDF, PNG, JPEG o WebP.",
                            file.name
                        );
                        continue;
                    }
                    if (file.size > MAX_FILE_BYTES) {
                        state.error = _t("«%s» supera el máximo de 10 MB.", file.name);
                        continue;
                    }
                    if (!file.size) {
                        state.error = _t("«%s» está vacío.", file.name);
                        continue;
                    }
                    state.error = null;
                    state.attachments.push(entry);
                    const item = state.attachments[state.attachments.length - 1];
                    item.uploading = true;
                    try {
                        const form = new FormData();
                        form.append("csrf_token", odoo.csrf_token);
                        form.append("conversation_id", state.conversationId);
                        form.append("ufile", file, file.name);
                        const response = await browser.fetch("/xtd_ai/chat/upload", {
                            method: "POST",
                            body: form,
                        });
                        const data = await response.json();
                        if (!response.ok || data.error) {
                            throw new Error(
                                data.error || _t("No se pudo subir el fichero.")
                            );
                        }
                        item.id = data.attachment_id;
                        item.name = data.name;
                        item.mimetype = data.mimetype;
                        item.size = data.size;
                    } catch (error) {
                        state.error = error.message;
                        const index = state.attachments.indexOf(item);
                        state.attachments.splice(
                            index >= 0 ? index : state.attachments.length,
                            1
                        );
                    } finally {
                        item.uploading = false;
                    }
                }
            },
            removeAttachment(key) {
                state.attachments = state.attachments.filter((a) => a.key !== key);
            },
            get uploading() {
                return state.attachments.some((a) => a.uploading);
            },
            /**
             * Send ``text`` (default: the draft) with the attached files. The draft is
             * restored if the call fails.
             */
            async send(text = null) {
                const fromDraft = text === null;
                text = (fromDraft ? state.draft : text || "").trim();
                const files = state.attachments.filter((a) => a.id);
                if (
                    (!text && !files.length) ||
                    service.uploading ||
                    state.runningRunId ||
                    state.busy ||
                    state.conversationState !== "open"
                ) {
                    return;
                }
                const savedDraft = state.draft;
                const savedFiles = state.attachments;
                state.busy = true;
                if (fromDraft) {
                    state.draft = "";
                }
                state.attachments = [];
                state.banner = null;
                try {
                    const res = await call("/xtd_ai/chat/send", {
                        text,
                        conversation_id: state.conversationId,
                        attachment_ids: files.map((a) => a.id),
                        // Companies active in the switcher (first one = current company)
                        company_ids: user.activeCompanies.map((c) => c.id),
                    });
                    state.runningRunId = res.state === "failed" ? null : res.run_id;
                } catch (error) {
                    if (fromDraft) {
                        state.draft = savedDraft;
                    }
                    state.attachments = savedFiles;
                    throw error;
                } finally {
                    state.busy = false;
                    await service.reload();
                }
            },
            async cancelRun() {
                if (!state.runningRunId) {
                    return;
                }
                try {
                    await call("/xtd_ai/chat/run/cancel", {run_id: state.runningRunId});
                } finally {
                    await service.reload();
                }
            },
            async confirmAction(actionId) {
                state.busy = true;
                try {
                    await call("/xtd_ai/chat/pending/confirm", {action_id: actionId});
                } finally {
                    state.busy = false;
                    await service.reload();
                }
            },
            async cancelAction(actionId) {
                state.busy = true;
                try {
                    await call("/xtd_ai/chat/pending/cancel", {action_id: actionId});
                } finally {
                    state.busy = false;
                    await service.reload();
                }
            },
            async setConfirmWrites(value) {
                state.settings = await call("/xtd_ai/chat/settings", {
                    confirm_writes: value,
                });
            },
        };

        service.restore();

        bus_service.subscribe("xtd_ai/update", (payload) => {
            if (payload && payload.conversation_id === state.conversationId) {
                service.reload();
                if (state.conversations.length) {
                    service.loadHistory();
                }
            }
        });
        return service;
    },
};

registry.category("services").add("xtd_ai_chat", xtdAiChatService);

export async function userHasAiGroup() {
    return user.hasGroup(XTD_AI_GROUP);
}
