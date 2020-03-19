from odoo import api, models, _


class AppointmentReport(models.AbstractModel):
    _name = 'report.om_hospital.appointment_report'
    _description = 'Appointment Report'

    @api.model
    def _get_report_values(self, docids, data=None):

        import logging ; logging.info("!"*80)

        appointments = self.env['hospital.appointment'].search([])
        # appointment_list = []
        # for app in appointments:
        #     vals = {
        #         'name': app.name,
        #         'notes': app.notes,
        #         'appointment_date': app.appointment_date
        #     }
        #     appointment_list.append(vals)
        return {
            'doc_model': 'hospital.patient',
            'appointments': appointments,
        }
