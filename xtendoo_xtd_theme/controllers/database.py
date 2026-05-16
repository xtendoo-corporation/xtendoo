# -*- coding: utf-8 -*-

from odoo.addons.web.controllers.database import Database


XTD_DB_MANAGER_REPLACEMENTS = {
    "<title>Odoo</title>": "<title>Xtd</title>",
    "/web/static/img/favicon.ico": "/xtendoo_xtd_theme/static/src/img/favicon.ico",
    "/web/static/img/logo2.png": "/xtendoo_xtd_theme/static/src/img/xtd_logo_negative.svg",
    "Warning, your Odoo database manager is not protected.": (
        "Warning, your Xtd database manager is not protected."
    ),
    "Warning, your Odoo database manager is not protected. To secure it, we have generated the following master password for it:": (
        "Warning, your Xtd database manager is not protected. To secure it, we have generated the following master password for it:"
    ),
    "To enhance your experience, some data may be sent to Odoo online services.": (
        "To enhance your experience, some data may be sent to Xtd online services."
    ),
    "https://www.odoo.com/privacy": "https://xtendoo.es/privacy-policy/",
    "In order to avoid conflicts between databases, Odoo needs to know if this database was moved or copied.": (
        "In order to avoid conflicts between databases, Xtd needs to know if this database was moved or copied."
    ),
}


def _apply_xtd_db_manager_branding(content):
    is_bytes = isinstance(content, bytes)
    body = content.decode("utf-8") if is_bytes else str(content)
    for source, target in XTD_DB_MANAGER_REPLACEMENTS.items():
        body = body.replace(source, target)
    if is_bytes:
        return body.encode("utf-8")
    return type(content)(body) if isinstance(content, str) else body


def _xtd_render_template(self, **values):
    response = Database._xtd_original_render_template(self, **values)
    if hasattr(response, "get_data") and hasattr(response, "set_data"):
        response.set_data(_apply_xtd_db_manager_branding(response.get_data()))
        return response
    return _apply_xtd_db_manager_branding(response)


if not hasattr(Database, "_xtd_original_render_template"):
    Database._xtd_original_render_template = Database._render_template
    Database._render_template = _xtd_render_template
