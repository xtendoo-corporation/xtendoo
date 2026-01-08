import {assignDefined, assignIn} from "@mail/utils/common/misc";
import {fields} from "@mail/core/common/record";
import {Thread} from "@mail/core/common/thread_model";
import {patch} from "@web/core/utils/patch";
import {url} from "@web/core/utils/urls";

patch(Thread, {
    _insert(data) {
        const thread = super._insert(...arguments);
        // En Thread el discriminante es `channel_type` (p.ej. "chat", "channel", "gateway").
        if (thread.channel_type === "gateway") {
            // `data.gateway_id` se gestiona en update(); aquí solo campos simples.
            assignIn(thread, data, ["anonymous_name"]);
            this.store.discuss.gateway.threads.add(thread);
        }
        return thread;
    },
});

patch(Thread.prototype, {
    gateway: fields.One("Gateway"),
    operator: fields.One("res.partner"),
    gateway_notifications: [],
    gateway_followers: fields.Many("GatewayFollower"),

    get isChatChannel() {
        return this.channel_type === "gateway" || super.isChatChannel;
    },
    get hasMemberList() {
        return this.channel_type === "gateway" || super.hasMemberList;
    },
    get avatarUrl() {
        if (this.channel_type !== "gateway") {
            return super.avatarUrl;
        }
        return url(
            `/web/image/discuss.channel/${this.id}/avatar_128`,
            assignDefined({}, {unique: this.avatarCacheKey})
        );
    },
    /** @param {Object} data */
    update(data) {
        super.update(data);
        if ("gateway_id" in data && this.channel_type === "gateway") {
            this.gateway = data.gateway_id;
        }
    },
    _computeDiscussAppCategory() {
        if (this.channel_type === "gateway") {
            return this.store.discuss.gateway;
        }
        return super._computeDiscussAppCategory(...arguments);
    },
});
