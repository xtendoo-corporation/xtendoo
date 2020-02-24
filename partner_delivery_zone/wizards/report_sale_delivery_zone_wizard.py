# Copyright  2018 Forest and Biomass Romania
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _, exceptions

import logging


class ReportSaleDeliveryZoneWizard(models.TransientModel):
    _name = "report.sale.delivery.zone.wizard"
    _description = "Report Sale Delivery Zone Wizard"

    user_id = fields.Many2one(
        'res.users',
        string='User',
    )
    partner_delivery_zone = fields.Many2one(
        comodel_name='partner.delivery.zone',
        string='Partner Delivery Zone',
    )
    date_report = fields.Date(
        required=True,
        default=fields.Date.context_today
    )

    @api.multi
    def button_report_sale_delivery_zone(self):
        self.ensure_one()

        action = self.env.ref(
            'partner_delivery_zone.invoice_payment_partner_delivery_zone')
        vals = action.read()[0]

        logging.info(vals)

        return vals

        return self.env.ref('account.account_invoices_without_payment').report_action(self)

        def _export(self, report_type):
            """Default export is PDF."""
            model = self.env['report_vat_report']
            report = model.create(self._prepare_vat_report())
            report.compute_data_for_report()
            return report.print_report(report_type)

        # data = {
        #     'model': "report.sale.delivery.zone.wizard",
        #     'form': self.read()[0]
        # }
        # logging.info("*"*80)
        # logging.info(data['form'])
        # return self.env.ref('partner_delivery_zone.demo_report_xml_view').report_action(self, data=data)

        # data = {
        #     'model': "report.sale.delivery.zone.wizard",
        #     'form': self.read()[0]
        # }
        # report = self.env['ir.actions.report'].search(
        #     [('report_name', '=', 'partner_delivery_zone.invoice_payment_partner_delivery_zone')],
        #     limit=1)
        #
        # logging.info(report)

        # invoices = self.env['account.invoice'].search([])
        # logging.info(invoices)


        # self.env['ir.actions.report']._get_report_from_name(
        #         'account.report_invoice'
        #     ).render_qweb_html(1)
        # raise exceptions.UserError(
        #     '%s / %s / %s' % (self.user_id, self.partner_delivery_zone, self.date_report)
        # )

    # @api.multi
    # def button_export_html(self):
    #     self.ensure_one()
    #     action = self.env.ref(
    #         'account_financial_report.action_report_vat_report')
    #     vals = action.read()[0]
    #     context1 = vals.get('context', {})
    #     if isinstance(context1, pycompat.string_types):
    #         context1 = safe_eval(context1)
    #     model = self.env['report_vat_report']
    #     report = model.create(self._prepare_vat_report())
    #     report.compute_data_for_report()
    #     context1['active_id'] = report.id
    #     context1['active_ids'] = report.ids
    #     vals['context'] = context1
    #     return vals
    #
    #
    # @api.multi
    # def button_export_pdf(self):
    #     self.ensure_one()
    #     report_type = 'qweb-pdf'
    #     return self._export(report_type)
    #
    #
    # @api.multi
    # def button_export_xlsx(self):
    #     self.ensure_one()
    #     report_type = 'xlsx'
    #     return self._export(report_type)
    #
    #
    # def _prepare_vat_report(self):
    #     self.ensure_one()
    #     return {
    #         'company_id': self.company_id.id,
    #         'date_from': self.date_from,
    #         'date_to': self.date_to,
    #         'based_on': self.based_on,
    #         'tax_detail': self.tax_detail,
    #     }
    #
    #
    # def _export(self, report_type):
    #     """Default export is PDF."""
    #     model = self.env['report_vat_report']
    #     report = model.create(self._prepare_vat_report())
    #     report.compute_data_for_report()
    #     return report.print_report(report_type)
