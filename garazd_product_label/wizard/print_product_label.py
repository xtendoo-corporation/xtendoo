# Copyright © 2018 Garazd Creation (<https://garazd.biz>)
# @author: Yurii Razumovskyi (<support@garazd.biz>)
# @author: Iryna Razumovska (<support@garazd.biz>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

from typing import List

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.base.models.res_partner import _lang_get


class PrintProductLabel(models.TransientModel):
    _name = "print.product.label"
    _description = 'Wizard to print Product Labels'

    @api.model
    def _complete_label_fields(self, label_ids: List[int]) -> List[int]:
        """Set additional fields for product labels. Method to override."""
        # Increase a label sequence
        labels = self.env['print.product.label.line'].browse(label_ids)
        for seq, label in enumerate(labels):
            label.sequence = 1000 + seq
        return label_ids

    @api.model
    def _get_product_label_ids(self):
        res = []
        # flake8: noqa: E501
        if self._context.get('active_model') == 'product.template':
            products = self.env[self._context.get('active_model')].browse(self._context.get('default_product_ids'))
            for product in products:
                label = self.env['print.product.label.line'].create({
                    'product_id': product.product_variant_id.id,
                })
                res.append(label.id)
        elif self._context.get('active_model') == 'product.product':
            products = self.env[self._context.get('active_model')].browse(self._context.get('default_product_ids'))
            for product in products:
                label = self.env['print.product.label.line'].create({
                    'product_id': product.id,
                })
                res.append(label.id)
        res = self._complete_label_fields(res)
        return res

    name = fields.Char(default='Print Product Labels')
    message = fields.Char(readonly=True)
    output = fields.Selection(
        selection=[('pdf', 'PDF')],
        string='Print to',
        default='pdf',
    )
    mode = fields.Selection(selection=[], help='Technical field')
    label_ids = fields.One2many(
        comodel_name='print.product.label.line',
        inverse_name='wizard_id',
        string='Labels for Products',
        default=_get_product_label_ids,
    )
    report_id = fields.Many2one(
        comodel_name='ir.actions.report',
        string='Label',
        domain=[('model', '=', 'print.product.label.line')],
    )
    is_template_report = fields.Boolean(compute='_compute_is_template_report')
    qty_per_product = fields.Integer(
        string='Label quantity per product',
        default=1,
    )
    # Options
    humanreadable = fields.Boolean(
        string='Human readable barcode',
        help='Print digital code of barcode.',
        default=False,
    )
    border_width = fields.Integer(
        string='Border',
        help='Border width for labels (in pixels). Set "0" for no border.'
    )
    lang = fields.Selection(
        selection=_lang_get,
        string='Language',
        help="The language that will be used to translate label names.",
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        help='Specify a company for product labels.'
    )

    @api.depends('report_id')
    def _compute_is_template_report(self):
        for wizard in self:
            # flake8: noqa: E501
            wizard.is_template_report = self.report_id == self.env.ref('garazd_product_label.action_report_product_label_from_template')

    def get_labels_to_print(self):
        self.ensure_one()
        labels = self.label_ids.filtered(lambda l: l.selected and l.qty)
        if not labels:
            raise UserError(
                _('Nothing to print, set the quantity of labels in the table.'))
        return labels

    def _get_report_action_params(self):
        """Return two params for a report action: record "ids" and "data"."""
        self.ensure_one()
        return self.get_labels_to_print().ids, None

    def _prepare_report(self):
        self.ensure_one()
        mode = self._context.get('print_mode', 'pdf')
        if not self.report_id:
            raise UserError(_('Please select a label type.'))
        report = self.report_id.with_context(discard_logo_check=True, lang=self.lang)
        report.sudo().write({'report_type': f'qweb-{mode}'})
        return report

    def action_print(self):
        """Print labels."""
        self.ensure_one()
        report = self._prepare_report()
        return report.report_action(*self._get_report_action_params())

    def action_set_qty(self):
        """Set a specific number of labels for all lines."""
        self.ensure_one()
        self.label_ids.write({'qty': self.qty_per_product})

    def action_restore_initial_qty(self):
        """Restore the initial number of labels for all lines."""
        self.ensure_one()
        for label in self.label_ids:
            if label.qty_initial:
                label.update({'qty': label.qty_initial})

    @api.model
    def _set_sequence(self, lbl, seq, processed):
        if lbl in processed:
            return seq, processed
        lbl.sequence = seq
        seq += 1
        processed += lbl
        return seq, processed

    def action_sort_by_product(self):
        self.ensure_one()
        sequence = 1000
        processed_labels = self.env['print.product.label.line'].browse()
        # flake8: noqa: E501
        for label in self.label_ids:
            sequence, processed_labels = self._set_sequence(label, sequence, processed_labels)
            tmpl_labels = self.label_ids.filtered(lambda l: l.product_id.product_tmpl_id == label.product_id.product_tmpl_id).sorted(lambda l: l.product_id.id, reverse=True) - label
            for tmpl_label in tmpl_labels:
                sequence, processed_labels = self._set_sequence(tmpl_label, sequence, processed_labels)
                product_labels = tmpl_labels.filtered(lambda l: l.product_id == label.product_id) - tmpl_label
                for product_label in product_labels:
                    sequence, processed_labels = self._set_sequence(product_label, sequence, processed_labels)
