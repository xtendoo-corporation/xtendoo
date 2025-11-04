# Copyright 2020 Manuel Calero - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class multiple_purchase_one_invoice_wizard(models.TransientModel):
    _name = "multiple.purchase.one.invoice.wizard"
    _description = "Purchase Order Payment Invoice"

    def create_invoices_for_purchase_order(self):
        purchase_ids = self._context.get("active_ids")
        purchase_order_obj = self.env["purchase.order"]
        purchase_order_line_obj = self.env["purchase.order.line"]
        ir_property_obj = self.env["ir.property"]
        inv_obj = self.env["account.move"]
        purchases = purchase_order_obj.browse(purchase_ids)

        # check all purchase order have one partner
        partner_ids = [order.partner_id for order in purchases if order.partner_id.id]
        partner_ids = list(set(partner_ids))
        if len(partner_ids) != 1:
            raise UserError(_("All Purchase Order should have same Supplier"))

        # check all purchase order have payment terms
        payment_term_id = [
            order.payment_term_id for order in purchases if order.payment_term_id.id
        ]
        payment_term_id = list(set(payment_term_id))
        if len(payment_term_id) != 1:
            raise UserError(_("All Purchase Order should have same Payment Terms"))

        # restrict partial invoiced
        for po in purchases:
            if po.state not in ["done", "purchase"] or po.invoice_count != 0:
                raise UserError(
                    _("All Purchase Order should be confirmed and uninvoiced")
                )

        origin_list = [order.name for order in purchases if order.name]
        origin = ",".join(origin_list)

        purchase_order_lines = purchase_order_line_obj.search(
            [("order_id", "in", purchase_ids)]
        )

        invoice_line_ids = []

        # Create Invoice Line
        for purchase_line in purchase_order_lines.filtered(lambda l: l.product_id):
            invoice_line_account_id = (
                purchase_line.product_id.property_account_expense_id.id
                or purchase_line.product_id.categ_id.property_account_expense_categ_id.id
                or False
            )
            if not invoice_line_account_id:
                inc_acc = ir_property_obj.get(
                    "property_account_expense_categ_id", "product.category"
                )
                invoice_line_account_id = (
                    purchase_line.order_id.fiscal_position_id.map_account(inc_acc).id
                    if inc_acc
                    else False
                )
            if not invoice_line_account_id:
                raise UserError(
                    _(
                        'There is no expense account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.'
                    )
                    % (purchase_line.product_id.name,)
                )

            taxes = purchase_line.taxes_id.filtered(
                lambda r: not purchase_line.company_id
                or r.company_id == purchase_line.company_id
            )
            if purchase_line.order_id.fiscal_position_id and taxes:
                tax_ids = purchase_line.order_id.fiscal_position_id.map_tax(taxes).ids
            else:
                tax_ids = taxes.ids
            if purchase_line.product_id.purchase_method == "purchase":
                qty = purchase_line.product_qty - purchase_line.qty_invoiced
            else:
                qty = purchase_line.qty_received - purchase_line.qty_invoiced
            invoice_line_vals = {
                "name": purchase_line.product_id.display_name or "",
                "account_id": invoice_line_account_id,
                "price_unit": purchase_line.price_unit,
                "quantity": qty,
                "discount": purchase_line.discount,
                "product_uom_id": purchase_line.product_id.uom_id.id,
                "product_id": purchase_line.product_id.id,
                "purchase_line_id": purchase_line.id,
                "tax_ids": [(6, 0, tax_ids)],
                "analytic_account_id": False,
            }

            invoice_line_ids.append((0, 0, invoice_line_vals))
        purchase_journals = self.env["account.journal"].search(
            [("type", "=", "purchase")]
        )
        invoice = inv_obj.create(
            {
                "name": "/",
                "invoice_origin": origin,
                "type": "in_invoice",
                "ref": False,
                "journal_id": purchase_journals and purchase_journals[0].id or False,
                "partner_id": partner_ids[0].id,
                "partner_shipping_id": partner_ids[0].id,
                "currency_id": partner_ids[0].currency_id.id,
                "fiscal_position_id": partner_ids[0].property_account_position_id.id,
                "team_id": False,
                "narration": "Invoice Created from single Invoice Process",
                "invoice_line_ids": invoice_line_ids,
                "company_id": partner_ids[0].company_id.id
                or self.env.user.company_id.id,
                "invoice_payment_term_id": payment_term_id[0].id,
                "purchase_id": purchase_line.order_id.id,
            }
        )

        if purchases:
            order = purchases[:-1]
        else:
            order = False
        for line in invoice.invoice_line_ids:
            line._get_computed_taxes()
        invoice.message_post_with_view(
            "mail.message_origin_link",
            values={"self": invoice, "origin": order},
            subtype_id=self.env.ref("mail.mt_note").id,
        )

        invoice_form = self.env.ref("account.view_move_form", False)
        return {
            "name": _("Vendor Invoice"),
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "account.move",
            "res_id": invoice.id,
            "views": [(invoice_form.id, "form")],
            "view_id": invoice_form.id,
            "target": "current",
        }
