# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class StockPickingBatch(models.Model):
    _inherit = ["stock.picking"]
    partner_phone = fields.Char(
        "TLF",
        related="partner_id.phone",
        readonly=True
    )
    comercial_id = fields.Many2one(
        string="Comercial",
        related="sale_id.user_id",
        store=True
    )
    payment_term = fields.Char(
        compute="compute_payment_term",
        string="Payment Term"
    )
    def compute_payment_term(self):
        for line in self.filtered(lambda l: l.sale_id != ""):
            line.payment_term = line.sale_id.payment_term_id.name
    invoice_id = fields.Many2one(
        "account.move",
        compute="get_invoice_id",
        string="Invoice"
    )
    def get_invoice_id(self):
        for picking in self:
            picking.invoice_id = ""
            if picking.picking_type_id.id == 8:
                if picking.origin != "":
                    invoice_id = self.env["account.move"].search(
                        [("invoice_origin", "like", picking.origin)], limit=1
                    )
                    picking.invoice_id = invoice_id

    is_backorder = fields.Boolean(
        compute="set_is_back_order",
        string="is BackOrder",
        default=lambda self: self._get_default_is_backorder(),
        store=True,
    )
    def set_is_back_order(self):
        for picking in self:
            if picking.origin is not False:
                picking.is_backorder = picking.origin.startswith("Retorno")
            else:
                picking.is_backorder = False

    def _get_default_is_backorder(self):
        if self.origin is not False:
            return self.origin.startswith("Retorno")
        else:
            return False

