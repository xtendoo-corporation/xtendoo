from odoo import models, fields, api, _
from datetime import date


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    has_overdue_invoices = fields.Boolean(
        string='Tiene Facturas Vencidas',
        compute='_compute_has_overdue_invoices',
        store=False
    )
    overdue_invoices_count = fields.Integer(
        string='Cantidad de Facturas Vencidas',
        compute='_compute_has_overdue_invoices',
        store=False
    )
    overdue_amount_total = fields.Monetary(
        string='Importe Total Vencido',
        compute='_compute_has_overdue_invoices',
        store=False,
        currency_field='currency_id'
    )
    partner_name_simple = fields.Char(
        string='Nombre del Cliente',
        compute='_compute_has_overdue_invoices',
        store=False
    )

    @api.depends('partner_id')
    def _compute_has_overdue_invoices(self):
        """Compute if the customer has overdue invoices"""
        for order in self:
            order.has_overdue_invoices = False
            order.overdue_invoices_count = 0
            order.overdue_amount_total = 0.0
            order.partner_name_simple = ''

            if order.partner_id:
                # Search for overdue invoices
                domain = [
                    ('partner_id', 'child_of', order.partner_id.commercial_partner_id.id),
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ['not_paid', 'partial']),
                    ('invoice_date_due', '<', date.today())
                ]

                overdue_invoices = self.env['account.move'].search(domain)

                if overdue_invoices:
                    order.has_overdue_invoices = True
                    order.overdue_invoices_count = len(overdue_invoices)
                    order.overdue_amount_total = sum(overdue_invoices.mapped('amount_residual'))

            # Set the simple partner name
            order.partner_name_simple = order.partner_id.name if order.partner_id else ''


    def action_show_overdue_invoices(self):
        """Action to show overdue invoices for the customer"""
        self.ensure_one()
        domain = [
            ('partner_id', 'child_of', self.partner_id.commercial_partner_id.id),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', date.today())
        ]

        return {
            'name': _('Facturas Vencidas'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {'default_move_type': 'out_invoice'},
        }
