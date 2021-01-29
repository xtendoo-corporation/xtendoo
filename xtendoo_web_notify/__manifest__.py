# pylint: disable=missing-docstring
# Copyright 2016 DDL-Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Xtendoo Web Notify",
    "summary": """
        Send notification messages to user""",
    "version": "13.0.1.0.1",
    "license": "AGPL-3",
    "author": "Xtendoo, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/web",
    "depends": ["web", "bus", "base"],
    "data": ["views/web_notify.xml", "views/res_users_demo.xml"],
    "installable": True,
}
