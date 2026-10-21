{
    "name": "AI Agent Chat",
    "summary": (
        "Floating window, full-page app and routes to chat with the AI agent from the "
        "Odoo web client"
    ),
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "license": "LGPL-3",
    "depends": ["xtd_ai_gateway", "web", "bus"],
    "data": ["views/xtd_ai_chat_menus.xml"],
    "assets": {
        "web.assets_backend": [
            "xtd_ai_chat/static/src/js/safe_markdown.esm.js",
            "xtd_ai_chat/static/src/js/chat_service.esm.js",
            "xtd_ai_chat/static/src/js/chat_conversation.esm.js",
            "xtd_ai_chat/static/src/js/chat_window.esm.js",
            "xtd_ai_chat/static/src/js/chat_app.esm.js",
            "xtd_ai_chat/static/src/js/chat_systray.esm.js",
            "xtd_ai_chat/static/src/xml/*.xml",
            "xtd_ai_chat/static/src/scss/*.scss",
        ],
        "web.assets_unit_tests": [
            "xtd_ai_chat/static/tests/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
