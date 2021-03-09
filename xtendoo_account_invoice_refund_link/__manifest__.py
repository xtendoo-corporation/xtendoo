# Copyright 2004-2011 Pexego Sistemas Informáticos. (http://pexego.es)
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2014-2017 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2021 Dani Domínguez - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Xtendoo Link refund invoice with original",
    "summary": " XtendooLink refund invoice with its original invoice",
    "version": "12.0.1.0.0",
    "category": "Accounting & Finance",
    "website": "https://github.com/OCA/account-invoicing",
    "author": "Pexego, Tecnativa, Xtendoo, Odoo Community Association (OCA)",
    "installable": True,
    "post_init_hook": "post_init_hook",
    "depends": [
        'account',
    ],
    "license": "AGPL-3",
    "data": [
        'views/account_invoice_view.xml',
    ],
}
