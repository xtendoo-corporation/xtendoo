# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Invoice Last Payment",
    "version": "15.0.1.0.1",
    "author": "Camilo Prado <Xtendoo>",
    "maintainers": ["Camilx03"],
    "category": "Accounting",
    "website": "https://github.com/xtendoo-corporation/xtendoo",
    "license": "AGPL-3",
    "depends": [
        "base",
        "account",
    ],
    "demo": [],
    "data": [
        "views/invoice_last_payment.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "auto_install": False,
}
