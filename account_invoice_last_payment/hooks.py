# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


def post_init_hook(env):
    """
    Backfill last payment date for existing posted invoices.
    """
    invoices = env["account.move"].search([
        ("state", "=", "posted"),
        ("move_type", "in", ("out_invoice", "out_refund", "in_invoice", "in_refund")),
    ])
    for invoice in invoices:
        invoice.last_payment = invoice._get_last_payment_date()
