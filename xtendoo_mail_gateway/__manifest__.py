# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Xtendoo Mail Gateway",
    "summary": "Base module for gateway communications",
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "author": "Xtendoo, Creu Blanca, Dixmit, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["mail"],
    "pre_init_hook": "pre_init_hook",
    "data": [
        "wizards/mail_compose_gateway_message.xml",
        "wizards/mail_message_gateway_link.xml",
        "wizards/mail_message_gateway_send.xml",
        "wizards/mail_guest_manage.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/mail_gateway.xml",
        "views/res_partner_gateway_channel.xml",
        "views/mail_guest_views.xml",
        "views/res_users_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # Components
            "xtendoo_mail_gateway/static/src/components/**/*",
            # Models
            "xtendoo_mail_gateway/static/src/models/**/*",
            # Core common patches
            "xtendoo_mail_gateway/static/src/core/common/composer_model_patch.esm.js",
            "xtendoo_mail_gateway/static/src/core/common/discuss_app_model_patch.esm.js",
            "xtendoo_mail_gateway/static/src/core/common/message_actions.esm.js",
            "xtendoo_mail_gateway/static/src/core/common/message_model_patch.esm.js",
            "xtendoo_mail_gateway/static/src/core/common/notification_model_patch.esm.js",
            "xtendoo_mail_gateway/static/src/core/common/store_service_patch.esm.js",
            "xtendoo_mail_gateway/static/src/core/common/thread_model_patch.esm.js",
            # Core web
            "xtendoo_mail_gateway/static/src/core/web/discuss_sidebar_category_item_patch.xml",
            "xtendoo_mail_gateway/static/src/core/web/gateway_core_web_service.esm.js",
            # Files excluded from bundle due to Odoo 19 incompatibility:
            # - core/common/mail_composer_send_dropdown.esm.js (MailComposerSendDropdown not in Odoo 19)
            # - core/common/mail_composer_send_dropdown.xml
            # - core/web/discuss_app_category_model_patch.esm.js (DiscussAppCategory not in Odoo 19)
        ],
        "web.assets_unit_tests": [
            "xtendoo_mail_gateway/static/tests/composer.test.js",
        ],
    },
}
