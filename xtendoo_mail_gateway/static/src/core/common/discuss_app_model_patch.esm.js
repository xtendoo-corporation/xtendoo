import { fields } from "@mail/core/common/record";
import { DiscussApp } from "@mail/core/public_web/discuss_app_model";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const discussAppGatewayPatch = {
    setup() {
        super.setup(...arguments);
        this.gateway = fields.One("DiscussAppCategory", {
            compute() {
                return {
                    extraClass: "o-mail-DiscussSidebarCategory-gateway",
                    id: "gateway",
                    name: _t("Gateway"),
                    isOpen: false,
                    canView: false,
                    canAdd: true,
                    addTitle: _t("Search Gateway Channel"),
                    serverStateKey: "is_discuss_sidebar_category_gateway_open",
                    sequence: 40,
                };
            },
            eager: true,
        });
    },
};

patch(DiscussApp.prototype, discussAppGatewayPatch);
