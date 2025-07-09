from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from datetime import datetime
import pytz

class PortalEmpleado(http.Controller):

    @http.route(['/mi/login_empleado'], type='http', auth='public', website=True, csrf=False)
    def login_empleado(self, **kwargs):
        return request.render('xtendoo_employees_portal.login_empleado')

    @http.route(['/mi/verificar_empleado'], type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def verificar_empleado(self, **post):
        pin = post.get('pin')
        if not pin:
            return request.redirect('/mi/login_empleado?error=pin_required')

        # Limpiar el PIN: solo remover espacios
        pin_clean = pin.strip()

        # Verificar que sea numérico
        if not pin_clean.isdigit():
            return request.redirect('/mi/login_empleado?error=pin_invalid')

        # Buscar empleado por PIN
        empleado = request.env['hr.employee'].sudo().search([
            ('pin', '=', pin_clean)
        ], limit=1)

        if empleado:
            request.session['empleado_id'] = empleado.id
            return request.redirect('/mi/dashboard')
        else:
            return request.redirect('/mi/login_empleado?error=pin_invalid')

    def get_empleado(self):
        eid = request.session.get('empleado_id')
        return request.env['hr.employee'].sudo().browse(eid) if eid else None

    def _convert_to_user_timezone(self, dt_utc):
        """Convierte datetime UTC a la zona horaria del usuario"""
        if not dt_utc:
            return None

        # Usar específicamente la zona horaria de Madrid para la visualización
        try:
            madrid_tz = pytz.timezone('Europe/Madrid')
            # Convertir de UTC a zona horaria de Madrid
            if dt_utc.tzinfo is None:
                dt_utc = pytz.utc.localize(dt_utc)
            return dt_utc.astimezone(madrid_tz)
        except:
            return dt_utc

    def _get_local_datetime(self):
        """Obtiene la fecha y hora actual en Madrid y la convierte a UTC para guardar en la base de datos"""
        madrid_tz = pytz.timezone('Europe/Madrid')
        now_madrid = datetime.now(madrid_tz)
        now_utc = now_madrid.astimezone(pytz.utc)
        return now_utc.replace(tzinfo=None)

    @http.route(['/mi/asistencias'], type='http', auth='public', website=True, csrf=False)
    def ver_asistencias(self, **kwargs):
        empleado = self.get_empleado()
        if not empleado:
            return request.redirect('/mi/login_empleado')

        asistencias = request.env['hr.attendance'].sudo().search([('employee_id', '=', empleado.id)], limit=30, order="check_in desc")

        # Procesar las asistencias para convertir las fechas
        asistencias_procesadas = []
        for asistencia in asistencias:
            check_in_local = self._convert_to_user_timezone(asistencia.check_in)
            check_out_local = self._convert_to_user_timezone(asistencia.check_out) if asistencia.check_out else None

            asistencias_procesadas.append({
                'id': asistencia.id,
                'check_in': asistencia.check_in,
                'check_out': asistencia.check_out,
                'check_in_local': check_in_local,
                'check_out_local': check_out_local,
                'worked_hours': asistencia.worked_hours,
                'fecha': check_in_local.date() if check_in_local else None,
                'hora_entrada': check_in_local.strftime('%H:%M') if check_in_local else '-',
                'hora_salida': check_out_local.strftime('%H:%M') if check_out_local else 'En curso',
            })

        return request.render('xtendoo_employees_portal.ver_asistencias', {
            'empleado': empleado,
            'asistencias': asistencias,
            'asistencias_procesadas': asistencias_procesadas
        })

    @http.route(['/mi/ausencias'], type='http', auth='public', website=True, csrf=False)
    def ver_ausencias(self, **kwargs):
        empleado = self.get_empleado()
        if not empleado:
            return request.redirect('/mi/login_empleado')
        ausencias = request.env['hr.leave'].sudo().search([('employee_id', '=', empleado.id)], order="request_date_from desc")
        return request.render('xtendoo_employees_portal.ver_ausencias', {'empleado': empleado, 'ausencias': ausencias})

    @http.route(['/mi/partes'], type='http', auth='public', website=True, csrf=False)
    def ver_partes(self, **kwargs):
        empleado = self.get_empleado()
        if not empleado:
            return request.redirect('/mi/login_empleado')
        partes = request.env['account.analytic.line'].sudo().search([('employee_id', '=', empleado.id)], order="date desc")
        return request.render('xtendoo_employees_portal.ver_partes', {'empleado': empleado, 'partes': partes})

    @http.route(['/mi/planificaciones'], type='http', auth='public', website=True, csrf=False)
    def ver_planificaciones(self, **kwargs):
        empleado = self.get_empleado()
        if not empleado:
            return request.redirect('/mi/login_empleado')

        # Buscar planificaciones del empleado en el modelo planning
        planificaciones = []

        # Intentar con diferentes modelos de planning según la versión
        planning_model = None
        if request.env['ir.model'].sudo().search([('model', '=', 'planning.slot')]):
            planning_model = 'planning.slot'
        elif request.env['ir.model'].sudo().search([('model', '=', 'planning.planning')]):
            planning_model = 'planning.planning'
        elif request.env['ir.model'].sudo().search([('model', '=', 'hr.planning.slot')]):
            planning_model = 'hr.planning.slot'

        if planning_model:
            # Buscar planificaciones del empleado
            domain = [('employee_id', '=', empleado.id)]

            # Filtrar por fechas recientes (últimas 4 semanas y próximas 4 semanas)
            from datetime import datetime, timedelta
            fecha_inicio = datetime.now() - timedelta(weeks=4)
            fecha_fin = datetime.now() + timedelta(weeks=4)

            if planning_model == 'planning.slot':
                domain.extend([
                    ('start_datetime', '>=', fecha_inicio),
                    ('end_datetime', '<=', fecha_fin)
                ])
                planning_records = request.env[planning_model].sudo().search(domain, order="start_datetime asc")

                # Procesar las planificaciones
                for slot in planning_records:
                    start_local = self._convert_to_user_timezone(slot.start_datetime)
                    end_local = self._convert_to_user_timezone(slot.end_datetime)

                    if start_local and end_local:
                        planificaciones.append({
                            'fecha': start_local.date(),
                            'fecha_str': start_local.strftime('%d/%m/%Y'),
                            'dia_semana': start_local.strftime('%A'),
                            'hora_inicio': start_local.strftime('%H:%M'),
                            'hora_fin': end_local.strftime('%H:%M'),
                            'duracion_horas': round((end_local - start_local).total_seconds() / 3600, 2),
                            'nombre': slot.name or 'Turno planificado',
                            'rol': getattr(slot, 'role_id', None) and slot.role_id.name or 'Sin rol',
                            'estado': getattr(slot, 'state', 'planificado'),
                            'template': getattr(slot, 'template_id', None) and slot.template_id.name or None
                        })
            else:
                # Para otros modelos de planning, adaptar según campos disponibles
                planning_records = request.env[planning_model].sudo().search(domain, order="date asc" if 'date' in request.env[planning_model]._fields else "id asc")

                for record in planning_records:
                    # Adaptar según los campos disponibles en el modelo
                    planificaciones.append({
                        'fecha': getattr(record, 'date', None) or getattr(record, 'start_date', None),
                        'fecha_str': (getattr(record, 'date', None) or getattr(record, 'start_date', None)).strftime('%d/%m/%Y') if (getattr(record, 'date', None) or getattr(record, 'start_date', None)) else 'Sin fecha',
                        'dia_semana': 'Planificado',
                        'hora_inicio': getattr(record, 'hour_from', None) or 'Sin hora',
                        'hora_fin': getattr(record, 'hour_to', None) or 'Sin hora',
                        'duracion_horas': getattr(record, 'duration', 0),
                        'nombre': record.name or 'Planificación',
                        'rol': 'N/A',
                        'estado': getattr(record, 'state', 'planificado'),
                        'template': None
                    })

        # Traducir días de la semana al español
        dias_es = {
            'Monday': 'Lunes',
            'Tuesday': 'Martes',
            'Wednesday': 'Miércoles',
            'Thursday': 'Jueves',
            'Friday': 'Viernes',
            'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        }

        for p in planificaciones:
            if p['dia_semana'] in dias_es:
                p['dia_semana'] = dias_es[p['dia_semana']]

        return request.render('xtendoo_employees_portal.ver_planificaciones', {
            'empleado': empleado,
            'planificaciones': planificaciones,
            'modelo_planning': planning_model or 'No encontrado',
            'total_planificaciones': len(planificaciones)
        })

    @http.route(['/mi/solicitar_ausencia'], type='http', auth='public', website=True, csrf=False)
    def solicitar_ausencia(self, **kwargs):
        empleado = self.get_empleado()
        if not empleado:
            return request.redirect('/mi/login_empleado')

        # Obtener los tipos de ausencia disponibles
        tipos_ausencia = request.env['hr.leave.type'].sudo().search([])

        return request.render('xtendoo_employees_portal.solicitar_ausencia', {
            'empleado': empleado,
            'tipos_ausencia': tipos_ausencia
        })

    @http.route(['/mi/procesar_solicitud_ausencia'], type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def procesar_solicitud_ausencia(self, **post):
        empleado = self.get_empleado()
        if not empleado:
            return request.redirect('/mi/login_empleado')

        # Validar datos requeridos
        tipo_ausencia = post.get('tipo_ausencia')
        fecha_inicio = post.get('request_date_from')
        fecha_fin = post.get('request_date_to')
        motivo = post.get('name')
        request_unit_half = post.get('request_unit_half', 'False')

        if not all([tipo_ausencia, fecha_inicio, fecha_fin, motivo]):
            return request.redirect('/mi/solicitar_ausencia?error=missing_data')

        # Validar fechas
        try:
            from datetime import datetime
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d').date()

            if fecha_fin_dt < fecha_inicio_dt:
                return request.redirect('/mi/solicitar_ausencia?error=invalid_dates')
        except ValueError:
            return request.redirect('/mi/solicitar_ausencia?error=invalid_dates')

        # Crear la solicitud de ausencia
        try:
            vals = {
                'name': motivo,
                'employee_id': empleado.id,
                'holiday_status_id': int(tipo_ausencia),
                'request_date_from': fecha_inicio,
                'request_date_to': fecha_fin,
                'request_unit_half': request_unit_half == 'True',
                'state': 'confirm',  # Estado pendiente de aprobación
            }

            # Crear la solicitud
            solicitud = request.env['hr.leave'].sudo().create(vals)

            # Redirigir con mensaje de éxito
            return request.redirect('/mi/solicitar_ausencia?success=1')

        except Exception as e:
            return request.redirect('/mi/solicitar_ausencia?error=missing_data')

    @http.route(['/mi/dashboard'], type='http', auth='public', website=True, csrf=False)
    def dashboard(self, **kwargs):
        empleado = self.get_empleado()
        if not empleado:
            return request.redirect('/mi/login_empleado')

        # Verificar si ya tiene fichaje abierto hoy
        today = datetime.now().date()
        asistencia_hoy = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', empleado.id),
            ('check_in', '>=', datetime.combine(today, datetime.min.time())),
            ('check_out', '=', False)
        ], limit=1)

        # Obtener la última asistencia para mostrar información
        ultima_asistencia = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', empleado.id)
        ], limit=1, order="check_in desc")

        # Obtener hora actual en zona horaria local de Madrid
        try:
            madrid_tz = pytz.timezone('Europe/Madrid')
            hora_actual_local = datetime.now(madrid_tz).strftime('%H:%M')
        except:
            hora_actual_local = datetime.now().strftime('%H:%M')

        # Procesar hora de asistencia abierta si existe
        asistencia_abierta_hora = None
        if asistencia_hoy:
            check_in_local = self._convert_to_user_timezone(asistencia_hoy.check_in)
            asistencia_abierta_hora = check_in_local.strftime('%H:%M') if check_in_local else '-'

        # Procesar última asistencia para mostrar en zona horaria local
        ultima_asistencia_procesada = None
        if ultima_asistencia:
            check_in_local = self._convert_to_user_timezone(ultima_asistencia.check_in)
            check_out_local = self._convert_to_user_timezone(ultima_asistencia.check_out) if ultima_asistencia.check_out else None

            ultima_asistencia_procesada = {
                'check_in_str': check_in_local.strftime('%d/%m/%Y %H:%M') if check_in_local else '-',
                'check_out_str': check_out_local.strftime('%d/%m/%Y %H:%M') if check_out_local else None,
                'worked_hours': ultima_asistencia.worked_hours
            }

        return request.render('xtendoo_employees_portal.dashboard', {
            'empleado': empleado,
            'asistencia_abierta': asistencia_hoy,
            'asistencia_abierta_hora': asistencia_abierta_hora,
            'ultima_asistencia': ultima_asistencia,
            'ultima_asistencia_procesada': ultima_asistencia_procesada,
            'hora_actual': hora_actual_local
        })

    @http.route(['/mi/fichar_entrada'], type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def fichar_entrada(self, **post):
        empleado = self.get_empleado()
        if not empleado:
            return request.redirect('/mi/login_empleado')

        # Verificar si ya tiene entrada hoy sin salida
        today = datetime.now().date()
        asistencia_abierta = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', empleado.id),
            ('check_in', '>=', datetime.combine(today, datetime.min.time())),
            ('check_out', '=', False)
        ], limit=1)

        if asistencia_abierta:
            return request.redirect('/mi/dashboard?error=already_checked_in')

        # Crear nuevo registro de entrada con hora local
        try:
            check_in_time = self._get_local_datetime()
            request.env['hr.attendance'].sudo().create({
                'employee_id': empleado.id,
                'check_in': check_in_time,
            })
            return request.redirect('/mi/dashboard?success=check_in')
        except Exception as e:
            return request.redirect('/mi/dashboard?error=check_in_failed')

    @http.route(['/mi/fichar_salida'], type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def fichar_salida(self, **post):
        empleado = self.get_empleado()
        if not empleado:
            return request.redirect('/mi/login_empleado')

        # Buscar asistencia abierta (sin check_out)
        asistencia_abierta = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', empleado.id),
            ('check_out', '=', False)
        ], limit=1, order="check_in desc")

        if not asistencia_abierta:
            return request.redirect('/mi/dashboard?error=no_check_in')

        # Registrar salida con hora local
        try:
            check_out_time = self._get_local_datetime()
            asistencia_abierta.write({
                'check_out': check_out_time
            })
            return request.redirect('/mi/dashboard?success=check_out')
        except Exception as e:
            return request.redirect('/mi/dashboard?error=check_out_failed')
