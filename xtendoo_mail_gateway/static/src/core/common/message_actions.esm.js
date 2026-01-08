import {_t} from "@web/core/l10n/translation";
import {messageActionsRegistry} from "@mail/core/common/message_actions";

messageActionsRegistry
    .add("link_gateway_to_thread", {
        condition: (component) => {
            const message = component.props?.message;
            const thread = component.props?.thread;
            return (
                message?.gateway_type &&
                thread?.model === "discuss.channel"
            );
        },
        icon: "fa fa-link",
        title: _t("Link to thread"),
        onClick: (component) => component.onClickLinkGatewayToThread(),
        sequence: 20,
    })
    .add("send_with_gateway", {
        condition: (component) => {
            const message = component.props?.message;
            const thread = component.props?.thread;
            return (
                message &&
                !message.gateway_type &&
                thread?.model !== "discuss.channel"
            );
        },
        icon: "fa fa-share-square-o",
        title: _t("Send with gateway"),
        onClick: (component) => component.onClickSendWithGateway(),
        sequence: 20,
    });
