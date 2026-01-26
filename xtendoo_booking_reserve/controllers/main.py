from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
import logging
import json
from pytz import timezone as pytz_timezone

class BookingReserveController(http.Controller):
    @http.route(['/booking/reserve'], type='http', auth='public', website=True)
    def booking_form(self, **kwargs):
        booking_types = http.request.env['resource.booking.type'].sudo().search([('active', '=', True)])
        return http.request.render('xtendoo_booking_reserve.booking_step_1', {
            'booking_types': booking_types,
        })

    @http.route('/booking/availability', type='json', auth='public')
    def booking_availability(self, type_id=None, start=None, end=None):
        logger = logging.getLogger(__name__)
        try:
            logger.info(f"Petición /booking/availability recibida con type_id={type_id}, start={start}, end={end}")
            if not type_id:
                logger.warning('No se ha especificado el tipo de cita en /booking/availability')
                return []
            try:
                type_id_int = int(type_id)
            except Exception as e:
                logger.error(f"type_id inválido: {type_id} - {str(e)}")
                return []
            booking_type = http.request.env['resource.booking.type'].sudo().browse(type_id_int)
            if not booking_type or not booking_type.exists():
                logger.warning(f'Tipo de cita no existe: {type_id} en /booking/availability')
                return []
            # Rango de fechas
            if start and end:
                try:
                    start_date = datetime.strptime(start, '%Y-%m-%d')
                    end_date = datetime.strptime(end, '%Y-%m-%d')
                except Exception as e:
                    logger.error(f"Fechas inválidas: start={start}, end={end} - {str(e)}")
                    return []
            else:
                today = datetime.today()
                start_date = today
                end_date = today + timedelta(days=30)
            days = []
            
            # Get resource calendar from booking type
            calendar = booking_type.resource_calendar_id
            if not calendar:
                logger.warning(f'No hay calendario asociado al tipo de cita: {type_id}')
                return []
            
            tz = pytz_timezone(calendar.tz or 'UTC')
            
            delta = (end_date - start_date).days
            for i in range(delta + 1):
                d = start_date + timedelta(days=i)
                # Check directly with calendar for this day
                date_start = tz.localize(datetime.combine(d, datetime.min.time()))
                date_end = date_start + timedelta(days=1)
                
                intervals = calendar._work_intervals_batch(date_start, date_end)[False]
                # If there are work intervals, the day is potentially available
                available = bool(intervals)
                
                # Further check: if fully booked? 
                # For basic day availability, checking if open is enough for now.
                # Detailed full-day capacity check would be heavier, 
                # but we can rely on hour selection to show 'No hours available'.
                
                days.append({'date': d.strftime('%Y-%m-%d'), 'available': available})
            
            logger.info(f"Respuesta /booking/availability: {days}")
            return days
        except Exception as e:
            logger.error(f'Error interno en /booking/availability: {str(e)}')
            return []

    @http.route('/booking/availability/hours', type='json', auth='public')
    def booking_availability_hours(self, type_id, date):
        """Get available hours from resource calendar"""
        logger = logging.getLogger(__name__)
        try:
            logger.info(f"Petición /booking/availability/hours recibida con type_id={type_id}, date={date}")
            try:
                type_id_int = int(type_id)
            except Exception as e:
                logger.error(f"type_id inválido: {type_id} - {str(e)}")
                return []
            
            booking_type = http.request.env['resource.booking.type'].sudo().browse(type_id_int)
            if not booking_type or not booking_type.exists():
                logger.warning(f'Tipo de cita no existe: {type_id}')
                return []
            
            # Get resource calendar from booking type
            calendar = booking_type.resource_calendar_id
            if not calendar:
                logger.warning(f'No hay calendario asociado al tipo de cita: {type_id}')
                return []
            
            # Parse date
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
            except Exception as e:
                logger.error(f"Fecha inválida: {date} - {str(e)}")
                return []
            
            # Get calendar timezone
            tz = pytz_timezone(calendar.tz or 'UTC')
            
            # Create datetime range for the day in calendar timezone
            date_start = tz.localize(date_obj.replace(hour=0, minute=0, second=0, microsecond=0))
            date_end = date_start + timedelta(days=1)
            
            # Get work intervals for this date
            intervals = calendar._work_intervals_batch(date_start, date_end)[False]
            
            hours = []
            slot_duration = timedelta(hours=booking_type.slot_duration or 0.5)
            booking_duration = timedelta(hours=booking_type.duration or 0.5)
            
            # Extract hours from intervals
            for interval_start, interval_end, _ in intervals._items:
                current = interval_start
                while current + booking_duration <= interval_end:
                    # Check if this slot overlaps with any existing booking
                    slot_end = current + booking_duration
                    
                    # Search for overlapping bookings
                    # We need to convert slot times to UTC for search as Odoo stores in UTC
                    slot_start_utc = current.astimezone(pytz_timezone('UTC')).replace(tzinfo=None)
                    slot_end_utc = slot_end.astimezone(pytz_timezone('UTC')).replace(tzinfo=None)
                    
                    domain = [
                        ('start', '<', slot_end_utc),
                        ('stop', '>', slot_start_utc),
                        ('state', '!=', 'rejected'), # Don't count rejected bookings
                        # If resource specific, add resource check. 
                        # Assuming pool or single resource for now based on type?
                        # If resource_booking uses combination, we might need more complex logic.
                        # For simple case: verify if there is capacity.
                        # If type has resources composed, we check if ALL are busy?
                        # Simplest: check if ANY booking overlaps if we assume 1 concurency per type/resource configuration.
                    ]
                    
                    # If the booking type is linked to specific resources, usually combinations handle it.
                    # But without combination logic exposed easily here, we check resource.booking directly.
                    # If the system allows multiple bookings at same time (capacity), logic differs.
                    # Assuming single capacity for now as requested "si un dia tiene muchas horas ocupadas...".
                    
                    overlap_count = http.request.env['resource.booking'].sudo().search_count(domain)
                    
                    # Logic: is capacity reached?
                    # If we don't handle capacity, any overlap = taken.
                    # If we assume 1 slot at a time:
                    if overlap_count == 0:
                        hour_str = current.strftime('%H:%M')
                        if hour_str not in hours:
                            hours.append(hour_str)
                    
                    current += slot_duration
            
            logger.info(f"Horas disponibles en calendario: {hours}")
            return hours
            
        except Exception as e:
            logger.error(f'Error interno en /booking/availability/hours: {str(e)}', exc_info=True)
            return []

    @http.route('/booking/reserve/submit', type='http', auth='public', methods=['POST'], website=True)
    def booking_reserve(self, **data):
        """Create booking request instead of direct booking"""
        logger = logging.getLogger(__name__)
        try:
            logger.info(f"Petición /booking/reserve/submit recibida con data={data}")
            type_id = data.get('type_id')
            name = data.get('name')
            phone = data.get('phone')
            email = data.get('email')
            date = data.get('date')
            hour = data.get('hour')
            
            if not type_id or not name or not phone or not date or not hour:
                logger.warning(f'Datos incompletos en /booking/reserve: {data}')
                return request.make_response(
                    json.dumps({'success': False, 'message': 'Datos incompletos'}),
                    headers=[('Content-Type', 'application/json')]
                )
            
            try:
                type_id_int = int(type_id)
            except Exception as e:
                logger.error(f"type_id inválido: {type_id} - {str(e)}")
                return request.make_response(
                    json.dumps({'success': False, 'message': 'Tipo de cita inválido'}),
                    headers=[('Content-Type', 'application/json')]
                )
            
            booking_type = http.request.env['resource.booking.type'].sudo().browse(type_id_int)
            if not booking_type or not booking_type.exists():
                logger.warning(f'Tipo de cita no existe: {type_id}')
                return request.make_response(
                    json.dumps({'success': False, 'message': 'Tipo de cita no encontrado'}),
                    headers=[('Content-Type', 'application/json')]
                )
            
            # Create booking request
            request_vals = {
                'name': name,
                'phone': phone,
                'email': email or False,
                'type_id': type_id_int,
                'booking_date': date,
                'booking_hour': hour,
                'state': 'pending',
            }
            
            booking_request = http.request.env['booking.request'].sudo().create(request_vals)
            logger.info(f"Solicitud de reserva creada: {booking_request.id}")
            
            return request.make_response(
                json.dumps({
                    'success': True,
                    'request_id': booking_request.id,
                    'message': 'Su solicitud ha sido enviada y será revisada pronto.'
                }),
                headers=[('Content-Type', 'application/json')]
            )
            
        except Exception as e:
            logger.error(f'Error interno en /booking/reserve: {str(e)}', exc_info=True)
            return request.make_response(
                json.dumps({'success': False, 'message': 'Error al procesar la solicitud'}),
                headers=[('Content-Type', 'application/json')]
            )
