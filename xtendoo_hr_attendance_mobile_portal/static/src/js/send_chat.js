import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";

/**
 * Copy the activation link to the clipboard and open the Discuss chat with the
 * employee's contact, with the link pre-filled in the composer.
 */
async function sendPortalLinkByChat(env, action) {
    const { partner_id: partnerId, text } = action.params;
    try {
        await browser.navigator.clipboard.writeText(text);
        env.services.notification.add(_t("Link copied to the clipboard."), {
            type: "success",
        });
    } catch {
        // Clipboard may be unavailable (insecure context): the text is still
        // pre-filled in the chat below.
    }
    const chat = await env.services["mail.store"].getChat({ partnerId });
    if (chat) {
        if (chat.composer) {
            chat.composer.composerText = text;
        }
        await chat.open({ focus: true });
    }
}

registry.category("actions").add("xtendoo_portal_send_chat", sendPortalLinkByChat);
