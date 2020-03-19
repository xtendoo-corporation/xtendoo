from odoo import api,fields, models, _
from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT


class ReportSaleDeliveryZone(models.AbstractModel):
    _name = 'report.partner_delivery_zone.report_sale_delivery_zone'
    _description = 'Appointment Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        PaymentDeliveryZoneModel = self.env['partner.delivery.zone']

        date_report = fields.Date.from_string(data['form'].get('date_report')) or fields.Date.today()
        doc_ids = tuple(data['active_ids'])
        docs = PaymentDeliveryZoneModel.browse(doc_ids)

        return {
            'docs': docs,
            'doc_ids': doc_ids,
            'doc_model': 'partner.delivery.zone',
            'date_report': date_report,
            'get_quotations_delivery_zone_date': self.get_quotations_delivery_zone_date,
            'get_sale_orders_delivery_zone_date': self.get_sale_orders_delivery_zone_date,
        }

    @api.model
    def get_quotations_delivery_zone_date(self, id, date):
        return self.env['sale.order'].search(
            [('delivery_zone_id', '=', id),
             ('state', '=', 'draft'),
             ('date_order', '>=', datetime.combine(date, datetime.min.time())),
             ('date_order', '<=', datetime.combine(date, datetime.max.time()))]
        )

    @api.model
    def get_sale_orders_delivery_zone_date(self, id, date):
        return self.env['sale.order'].search(
            [('delivery_zone_id', '=', id),
             ('state', '!=', 'draft'),
             ('date_order', '>=', datetime.combine(date, datetime.min.time())),
             ('date_order', '<=', datetime.combine(date, datetime.max.time()))]
        )
