# Copyright 2021 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_invoice_pdf_proforma(self):
        """ Generate the Proforma of the invoice.
        :return dict: the Proforma's data such as
        {'filename': 'INV_2024_0001_proforma.pdf', 'filetype': 'pdf', 'content': ...}
        """
        self.ensure_one()
        filename = self._get_invoice_proforma_pdf_report_filename()
        content, report_type = self.env['ir.actions.report']._pre_render_qweb_pdf('account.account_invoices', self.ids,
                                                                                  data={'proforma': False})
        content_by_id = self.env['ir.actions.report']._get_splitted_report('account.account_invoices', content,
                                                                           report_type)
        return {
            'filename': filename,
            'filetype': 'pdf',
            'content': content_by_id[self.id],
        }

    def _get_invoice_proforma_pdf_report_filename(self):
        """ Get the filename of the generated proforma PDF invoice report. """
        self.ensure_one()
        return f"{self._get_move_display_name().replace(' ', '_').replace('/', '_')}.pdf"
