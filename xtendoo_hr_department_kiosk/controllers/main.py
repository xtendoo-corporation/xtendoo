# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.hr_attendance.controllers.main import HrAttendance


class HrAttendanceXtendoo(HrAttendance):

    @http.route(["/hr_attendance/<token>"], type='http', auth='public', website=True, sitemap=True)
    def open_kiosk_mode(self, token, from_trial_mode=False, **kw):
        """Extiende la ruta original para capturar el department_id de los argumentos"""
        department_id = kw.get('department_id')
        
        # Llamamos al método original
        response = super().open_kiosk_mode(token, from_trial_mode=from_trial_mode)
        
        # Si la respuesta es un renderizado (qcontext existe) e inyectamos el department_id
        if hasattr(response, 'qcontext') and department_id:
            try:
                response.qcontext['kiosk_backend_info']['department_id'] = int(department_id)
            except (ValueError, TypeError):
                pass
            
        return response
