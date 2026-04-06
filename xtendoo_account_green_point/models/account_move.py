from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_total_green_point = fields.Monetary(
        string="Total Punto Verde", compute="_compute_green_point_totals", store=True
    )
    amount_untaxed_with_green_point = fields.Monetary(
        string="Base Imponible + PV", compute="_compute_green_point_totals", store=True
    )

    @api.depends("line_ids.green_point_amount_line", "amount_untaxed")
    def _compute_green_point_totals(self):
        for move in self:
            gp_total = sum(
                move.invoice_line_ids.filtered(
                    lambda l: l.display_type in ("product", False, "")
                ).mapped("green_point_amount_line")
            )
            move.amount_total_green_point = gp_total
            move.amount_untaxed_with_green_point = move.amount_untaxed + gp_total

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        # Write back Green Point unit value to product template on vendor bill validation
        for move in self:
            if move.move_type in ("in_invoice", "in_receipt"):
                for line in move.invoice_line_ids.filtered(
                    lambda l: l.product_id and l.green_point_applicable
                ):
                    if line.green_point_amount_unit:
                        line.product_id.product_tmpl_id.green_point_amount = (
                            line.green_point_amount_unit
                        )
        return res
