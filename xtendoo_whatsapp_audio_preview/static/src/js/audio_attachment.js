/** @odoo-module **/

import { AttachmentList } from "@mail/core/common/attachment_list";
import { patch } from "@web/core/utils/patch";

const AUDIO_MIMETYPES = [
    "audio/ogg",
    "audio/opus",
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/aac",
    "audio/mp4",
    "audio/amr",
];

patch(AttachmentList.prototype, {
    /**
     * Check if an attachment is an audio file, including WhatsApp voice notes.
     * @param {Object} attachment
     * @returns {boolean}
     */
    isAudioAttachment(attachment) {
        if (attachment.voice) {
            // Native Odoo voice messages already use VoicePlayer.
            return false;
        }
        const mimetype = (attachment.mimetype || "").toLowerCase();
        return AUDIO_MIMETYPES.some((type) => mimetype.startsWith(type));
    },

    /**
     * Get the URL to stream the audio file.
     * @param {Object} attachment
     * @returns {string}
     */
    getAudioUrl(attachment) {
        if (attachment.tmpUrl) {
            return attachment.tmpUrl;
        }
        return `/web/content/${attachment.id}?download=false`;
    },
});
