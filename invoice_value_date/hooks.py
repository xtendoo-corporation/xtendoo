# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import ast
from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """ Set value for order_sequence on old records """
    cr.execute("""
        update account_invoice
        set date_value = date_invoice
        where date_value is null
    """)

