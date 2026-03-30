/** @odoo-module */


import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

patch(PosStore.prototype, {
    openCashbox() {
        $("<center><div id='content_id'>Open Cash Drawer</div></center>").print();
    }
});


