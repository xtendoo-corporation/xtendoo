import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/core/common/record";
import { patch } from "@web/core/utils/patch";

// Campos que el servidor envía en discuss.channel._to_store (ver models/discuss_channel.py).
// En 19 hay que declararlos en el modelo del cliente para que el Store los guarde.
patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.whatsapp_phone = fields.Attr("");
        this.whatsapp_odoo_contact_label = fields.Attr("");
        this.whatsapp_partner_matches = fields.Attr(undefined);
    },
});
