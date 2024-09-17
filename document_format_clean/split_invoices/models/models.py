# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

from odoo.tools import float_compare


class InheritStockPicking(models.Model):
    _inherit = 'account.move'

    splitted_invoice_count = fields.Integer(string='Invoice Count', compute='_get_invoiced', readonly=True)
    split_count = fields.Integer()
    source_invoice_id = fields.Many2one('account.move')
    invoice_sources = fields.Char()

    def split_invoice_wizard(self):
        active_ids = self.env.context.get('active_ids', False)
        invoice_id = self.env['account.move'].browse(active_ids)
        if invoice_id.state != 'draft':
            raise ValidationError('Posted invoice cannot split.')
        move_line_ids = []
        for line_id in invoice_id.invoice_line_ids:
            move_line_ids.append((0, 0, {
                'invoice_line_id': line_id.id,
                'product_id': line_id.product_id.id,
                'quantity': line_id.quantity,
                'price': line_id.price_unit,
                'uom_id': line_id.product_uom_id.id,
                'tax_ids': line_id.tax_ids.ids,
            }))
        return {
            'name': 'Split Wizard',
            'res_model': 'split.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': invoice_id.partner_id.id,
                'default_move_type': invoice_id.move_type,
                'default_origin': invoice_id.ref,
                'default_invoice_sources': invoice_id.name,
                'default_move_line_ids': move_line_ids,
                'default_invoice_id': invoice_id.id,
            },
            'type': 'ir.actions.act_window'
        }

    def _get_invoiced(self):
        for rec in self:
            invoices = self.env['account.move'].sudo().search([('source_invoice_id', '=', rec.id)])
            if invoices:
                rec.splitted_invoice_count = len(invoices)

            else:
                rec.splitted_invoice_count = 0

    def action_view_invoice(self):
        invoices = self.env['account.move'].search([('source_invoice_id', '=', self.id)])
        action = self.env["ir.actions.actions"].sudo()._for_xml_id("account.action_move_out_invoice_type")
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,

                'default_invoice_payment_term_id': self.env['account.move'].sudo().default_get(
                    ['invoice_payment_term_id']).get('invoice_payment_term_id'),
            })
        action['context'] = context
        return action


# def compare_price_of_list(price_list, precision_digits):
#     final_price_list = []
#     for i in range(len(price_list)):
#         for j in range(len(price_list)):
#             if j > i:
#                 resp = float_compare(price_list[i], price_list[j], precision_digits=precision_digits)
#                 if resp == 0:
#                     final_price_list.append(price_list[i])
#                 else:
#                     final_price_list.append(price_list[i])
#                     final_price_list.append(price_list[j])
#     return list(set(final_price_list))


class SplitPickingWizard(models.TransientModel):
    _name = 'split.invoice.wizard'

    origin = fields.Char('Source Document', help="Reference of the document")
    invoice_sources = fields.Char()
    partner_id = fields.Many2one('res.partner', 'Contact', )
    split_type = fields.Selection(
        [('quantity_per', 'Quantity on Percentage'), ('quantity_line', 'Quantity as per line'),
         ('manual', 'Manual Remove line')], required=True)
    quantity_percentage = fields.Float()
    quantity_percentage_second = fields.Float()

    move_line_ids = fields.One2many('wizard.move.line', 'wizard_id')
    invoice_id = fields.Many2one('account.move', )
    move_type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Credit Note'),
        ('in_refund', 'Vendor Credit Note'),
    ])

    @api.onchange('quantity_percentage')
    def onchange_quantity_percentage(self, ):
        self.quantity_percentage_second = 100 - self.quantity_percentage

    @api.onchange('quantity_percentage_second')
    def onchange_quantity_percentage_second(self, ):
        self.quantity_percentage = 100 - self.quantity_percentage_second

    @api.onchange('split_type')
    def onchange_split_type(self, ):
        self.reset_form()
        self.quantity_percentage_second = 100
        self.quantity_percentage = 0

    def reset_form(self):
        move_line_ids = []
        for line_id in self.invoice_id.invoice_line_ids:
            move_line_ids.append((0, 0, {
                'invoice_line_id': line_id.id,
                'product_id': line_id.product_id.id,
                'quantity': line_id.quantity,
                'price': line_id.price_unit,
                'uom_id': line_id.product_uom_id.id,
                'tax_ids': line_id.tax_ids.ids,
            }))
        self.move_line_ids = False
        self.move_line_ids = move_line_ids

    def can_inv_split(self):
        is_changed = False

        if len(self.move_line_ids) != len(self.invoice_id.invoice_line_ids):
            is_changed = True

        else:
            for inv_line_id in self.invoice_id.invoice_line_ids:
                self_line = self.move_line_ids.filtered(lambda l: l.product_id == inv_line_id.product_id)
                for line in self_line:
                    if line.quantity != inv_line_id.quantity:
                        is_changed = True

        return is_changed

    def split_invoice(self):
        move_lines = []
        if self.split_type == 'quantity_per' and (
                self.quantity_percentage in [0, 100] or self.quantity_percentage_second in [0, 100]):
            raise ValidationError('Percentage cannot be 0')
        if self.split_type != 'quantity_per' and not self.can_inv_split():
            raise ValidationError('Invoice cannot be split')
        inv_data1 = {
            'move_type': self.move_type,
            'source_invoice_id': self.invoice_id.id,
            'partner_id': self.partner_id.id,
            'ref': self.origin,
            'invoice_sources': self.invoice_sources,
        }
        inv_data2 = {
            'move_type': self.move_type,
            'source_invoice_id': self.invoice_id.id,
            'partner_id': self.partner_id.id,
            'ref': self.origin,
            'invoice_sources': self.invoice_sources,
        }
        if self.split_type == 'quantity_per':
            inv_line1 = []
            inv_line2 = []
            for line in self.move_line_ids:
                inv_line1.append((0, 0, {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'quantity': line.quantity * self.quantity_percentage / 100,
                    'price_unit': line.price,
                    'tax_ids': line.tax_ids.ids,
                    'product_uom_id': line.uom_id.id,
                }))
                inv_line2.append((0, 0, {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'quantity': line.quantity * self.quantity_percentage_second / 100,
                    'price_unit': line.price,
                    'tax_ids': line.tax_ids.ids,
                    'product_uom_id': line.uom_id.id,
                }))
            inv_data1.update({'invoice_line_ids': inv_line1})
            inv_data2.update({'invoice_line_ids': inv_line2})
        else:
            inv_line1 = []
            inv_line2 = []
            for inv_line in self.invoice_id.invoice_line_ids:
                self_inv_line = self.move_line_ids.filtered(lambda l: l.invoice_line_id.id == inv_line.id)
                if self_inv_line:
                    quantity = self_inv_line.quantity if self_inv_line.quantity != inv_line.quantity else inv_line.quantity
                    print('inv line 1', quantity)
                    inv_line1.append((0, 0, {
                        'name': inv_line.product_id.name,
                        'product_id': inv_line.product_id.id,
                        'quantity': quantity,
                        'price_unit': inv_line.price_unit,
                        'tax_ids': inv_line.tax_ids.ids,
                        'product_uom_id': inv_line.product_uom_id.id,
                    }))
                if self_inv_line.quantity != inv_line.quantity or not self_inv_line:
                    quantity = inv_line.quantity - self_inv_line.quantity if self_inv_line else inv_line.quantity
                    print('inv line 2', quantity, self_inv_line)
                    inv_line2.append((0, 0, {
                        'name': inv_line.product_id.name,
                        'product_id': inv_line.product_id.id,
                        'quantity': quantity,
                        'price_unit': inv_line.price_unit,
                        'tax_ids': inv_line.tax_ids.ids,
                        'product_uom_id': inv_line.product_uom_id.id,
                    }))
            inv_data1.update({'invoice_line_ids': inv_line1})
            inv_data2.update({'invoice_line_ids': inv_line2})
        inv_data_list = [inv_data1, inv_data2]

        invoice_ids = self.env['account.move'].create(inv_data_list)

        if invoice_ids:
            for inv in self.invoice_id:
                inv.button_cancel()

        # return {
        #     'name': 'Invoices',
        #     'view_mode': 'list,form',
        #     'view_id': False,
        #     'res_model': 'account.move',
        #     'type': 'ir.actions.act_window',
        #     'target': 'current',
        #     'domain': [('id','in',invoice_ids.ids)],
        #     'res_id': invoice_ids.ids,
        # }


class WizardMoveLine(models.TransientModel):
    _name = 'wizard.move.line'

    product_id = fields.Many2one('product.product')
    invoice_line_id = fields.Many2one('account.move.line')
    quantity = fields.Float()
    price = fields.Monetary()
    tax_ids = fields.Many2many('account.tax')
    wizard_id = fields.Many2one('split.invoice.wizard')
    uom_id = fields.Many2one('uom.uom')
    currency_id = fields.Many2one(related='wizard_id.invoice_id.currency_id')
