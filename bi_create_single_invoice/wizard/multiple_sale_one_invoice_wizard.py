# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _
from odoo.exceptions import UserError


class multiple_sale_one_invoice_wizard(models.TransientModel):
    _name = 'multiple.sale.one.invoice.wizard'

    def create_invoices_for_sale_order(self):
        sale_ids = self._context.get('active_ids')
        sale_order_obj = self.env['sale.order']
        sale_order_line_obj = self.env['sale.order.line']
        ir_property_obj = self.env['ir.property']
        inv_obj = self.env['account.move']
        uid = self._uid
        current_user = self.env['res.users'].browse(uid)
        sales = sale_order_obj.browse(sale_ids)

        # check all sale order have one partner
        partner_ids = [order.partner_id for order in sales if order.partner_id.id]
        partner_ids = list(set(partner_ids))
        if len(partner_ids) != 1:
            raise UserError(_("All Sale Order should have same customer"))

        payment_term_id = [order.payment_term_id for order in sales if order.payment_term_id.id]
        payment_term_id = list(set(payment_term_id))
        if len(payment_term_id) != 1:
            raise UserError(_("All Sale Order should have same Payment Term"))

        # restrict partial invoiced
        valid_sale_orders = sale_order_obj.search(
            [('partner_id', '=', partner_ids[0].id), ('state', 'in', ['sale', 'done'])])
        valid_sale_order_ids = map(int, valid_sale_orders)

        for sale in sales:
            if sale.id not in valid_sale_order_ids or sale.invoice_count != 0:
                raise UserError(_("All Sale Order should be confirmed and uninvoiced"))

        origin_list = [order.name for order in sales if order.name]
        origin = ','.join(origin_list)

        sale_order_lines = sale_order_line_obj.search([('order_id', 'in', sale_ids)])
        account_id = partner_ids[0].property_account_receivable_id.id or False
        invoice_line_ids = []

        # Create Invoice Line
        for sale_line in sale_order_lines:

            invoice_line_account_id = False
            if sale_line.product_id.id:
                invoice_line_account_id = sale_line.product_id.property_account_income_id.id or sale_line.product_id.categ_id.property_account_income_categ_id.id or False
            if not invoice_line_account_id:
                inc_acc = ir_property_obj.get('property_account_income_categ_id', 'product.category')
                invoice_line_account_id = sale_line.order_id.fiscal_position_id.map_account(
                    inc_acc).id if inc_acc else False
            if not invoice_line_account_id:
                raise UserError(
                    _(
                        'There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') %
                    (sale_line.product_id.name,))

            taxes = sale_line.tax_id.filtered(
                lambda r: not sale_line.company_id or r.company_id == sale_line.company_id)
            tax_ids = []
            if sale_line.order_id.fiscal_position_id and taxes:
                tax_ids = sale_line.order_id.fiscal_position_id.map_tax(taxes).ids
            else:
                tax_ids = taxes.ids

            invoice_line_vals = {
                'name': sale_line.product_id.display_name or '',
                # 'origin': sale_line.order_id.name,
                'account_id': invoice_line_account_id,
                'price_unit': sale_line.price_unit,
                'quantity': sale_line.product_uom_qty,
                'discount': 0.0,
                'product_uom_id': sale_line.product_id.uom_id.id,
                'product_id': sale_line.product_id.id,
                'sale_line_ids': [(6, 0, [sale_line.id])],
                'tax_ids': [(6, 0, tax_ids)],
                'analytic_account_id': False,
            }

            invoice_line_ids.append((0, 0, invoice_line_vals))
        sale_journals = self.env['account.journal'].search([('type', '=', 'sale')])
        invoice = inv_obj.create({
            'name': "/",
            'invoice_origin': origin,
            'type': 'out_invoice',
            'ref': False,
            'journal_id': sale_journals and sale_journals[0].id or False,
            'partner_id': partner_ids[0].id,
            'partner_shipping_id': partner_ids[0].id,
            'currency_id': partner_ids[0].currency_id.id,
            'invoice_payment_term_id': False,
            'fiscal_position_id': partner_ids[0].property_account_position_id.id,
            'team_id': False,
            'narration': "Invoice Created from single Invoice Process",
            'invoice_line_ids': invoice_line_ids,
            'company_id': partner_ids[0].company_id.id or self.env.user.company_id.id,
            'invoice_payment_term_id': payment_term_id[0].id,
        })
        if sales:
            order = sales[:-1]
        else:
            order = False
        for line in invoice.invoice_line_ids:
            line._get_computed_taxes()
        invoice.message_post_with_view('mail.message_origin_link',
                                       values={'self': invoice, 'origin': order},
                                       subtype_id=self.env.ref('mail.mt_note').id)

        invoice_form = self.env.ref('account.view_move_form', False)
        return {
            'name': _('Customer Invoice'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'views': [(invoice_form.id, 'form')],
            'view_id': invoice_form.id,
            'target': 'current',
        }

# # vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
