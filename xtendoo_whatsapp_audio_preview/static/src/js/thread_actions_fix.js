import { _t } from "@web/core/l10n/translation";
import { threadActionsRegistry } from "@mail/core/common/thread_actions";

// OCA mail_gateway (19.0) registra las acciones "open-gw-new-partner" y "open-gw-profile" con una
// `condition` que lanza peticiones RPC y llama a `owner.render()` DURANTE el render del hilo. Con este
// core de 19 eso bloquea el pintado de la lista de mensajes (aparece el chat pero no los mensajes).
// Se sustituyen por una acción "Abrir contacto" sin efectos secundarios, que usa los datos que ya envía
// el servidor en `whatsapp_partner_matches` (ver models/discuss_channel.py).
for (const name of ["open-gw-new-partner", "open-gw-profile"]) {
    if (threadActionsRegistry.contains(name)) {
        threadActionsRegistry.remove(name);
    }
}

threadActionsRegistry.add("open-xtd-wa-contact", {
    condition({ owner, thread }) {
        if (
            thread?.model !== "discuss.channel" ||
            (owner.props.chatWindow && !owner.props.chatWindow.isOpen)
        ) {
            return false;
        }
        return Boolean(thread.whatsapp_partner_matches?.length);
    },
    icon: "fa fa-fw fa-user-circle-o",
    iconLarge: "fa fa-fw fa-lg fa-user-circle-o",
    name: _t("Open Contact"),
    async open({ owner, thread }) {
        const partnerId = thread.whatsapp_partner_matches?.[0]?.id;
        if (!partnerId) {
            return;
        }
        await owner.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
        });
    },
    sequence: 17,
});
