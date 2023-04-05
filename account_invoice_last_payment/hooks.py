# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID
from odoo.api import Environment


def post_init_hook(cr, pool):
    """
    Fetches all invoice and recomputed invoice
    """
    env = Environment(cr, SUPERUSER_ID, {})
    invoices = env["account.move"].search([])
    invoices._compute_amount()
