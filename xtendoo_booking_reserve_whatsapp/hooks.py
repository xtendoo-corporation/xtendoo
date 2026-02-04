import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    """Create default WhatsApp templates if a gateway exists."""
    gateway = env['mail.gateway'].search([('gateway_type', '=', 'whatsapp')], limit=1)
    if not gateway:
        _logger.warning("No WhatsApp gateway found. Skipping creation of default WhatsApp templates.")
        return

    # Common variable structure
    variables = [
        (0, 0, {'name': '{{1}}', 'line_type': 'body', 'field_type': 'field', 'field_name': 'name', 'demo_value': 'Juan Pérez'}),
        (0, 0, {'name': '{{2}}', 'line_type': 'body', 'field_type': 'field', 'field_name': 'booking_date', 'demo_value': '2023-10-25'}),
        (0, 0, {'name': '{{3}}', 'line_type': 'body', 'field_type': 'field', 'field_name': 'booking_hour', 'demo_value': '10:00'}),
    ]

    # Reminder Template
    values_reminder = {
        'name': 'Recordatorio Cita WhatsApp',
        'model_id': env.ref('xtendoo_booking_reserve.model_booking_request').id,
        'gateway_id': gateway.id,
        'category': 'utility',
        'language': 'es_ES',
        'body': 'Hola {{1}}, le recordamos su cita para el {{2}} a las {{3}}. ¡Gracias!',
        'variable_ids': [v for v in variables] # Copy list logic if needed, but tuples are immutable refs so it's fine as structure source
    }
    # Check if exists
    if not env['mail.whatsapp.template'].search([('name', '=', values_reminder['name']), ('model_id', '=', values_reminder['model_id'])]):
        env['mail.whatsapp.template'].create(values_reminder)

    # Approved Template
    values_approved = {
        'name': 'Cita Aprobada WhatsApp',
        'model_id': env.ref('xtendoo_booking_reserve.model_booking_request').id,
        'gateway_id': gateway.id,
        'category': 'utility',
        'language': 'es_ES',
        'body': 'Hola {{1}}, su solicitud de cita para el {{2}} a las {{3}} ha sido APROBADA. Le esperamos.',
        'variable_ids': [(0, 0, v[2]) for v in variables] # Recreate to avoid sharing ORM stack issues if any validation checks ids
    }
    if not env['mail.whatsapp.template'].search([('name', '=', values_approved['name']), ('model_id', '=', values_approved['model_id'])]):
        env['mail.whatsapp.template'].create(values_approved)

    # Rejected Template
    values_rejected = {
        'name': 'Cita Rechazada WhatsApp',
        'model_id': env.ref('xtendoo_booking_reserve.model_booking_request').id,
        'gateway_id': gateway.id,
        'category': 'utility',
        'language': 'es_ES',
        'body': 'Hola {{1}}, lamentamos informarle que su solicitud de cita para el {{2}} a las {{3}} ha sido RECHAZADA. Contacte con nosotros.',
        'variable_ids': [(0, 0, v[2]) for v in variables]
    }
    if not env['mail.whatsapp.template'].search([('name', '=', values_rejected['name']), ('model_id', '=', values_rejected['model_id'])]):
        env['mail.whatsapp.template'].create(values_rejected)

    # Template de Recordatorio para Calendar Event
    calendar_event_model = env['ir.model'].search([('model', '=', 'calendar.event')], limit=1)
    if calendar_event_model:
        values_calendar_reminder = {
            'name': 'Recordatorio Cita WhatsApp',
            'model_id': calendar_event_model.id,
            'gateway_id': gateway.id,
            'category': 'utility',
            'language': 'es_ES',
            'body': 'Hola, le recordamos su cita: {{1}} el {{2}}. ¡Gracias!',
            'variable_ids': [
                (0, 0, {'name': '{{1}}', 'line_type': 'body', 'field_type': 'field', 'field_name': 'name', 'demo_value': 'Cita Médica'}),
                (0, 0, {'name': '{{2}}', 'line_type': 'body', 'field_type': 'field', 'field_name': 'start', 'demo_value': '2023-10-25 10:00'}),
            ]
        }
        calendar_template = env['mail.whatsapp.template'].search([
            ('name', '=', values_calendar_reminder['name']),
            ('model_id', '=', calendar_event_model.id)
        ])
        if not calendar_template:
            calendar_template = env['mail.whatsapp.template'].create(values_calendar_reminder)
            _logger.info("Template 'Recordatorio Cita WhatsApp' creado para calendar.event (ID: %s)", calendar_template.id)

        # Crear alarma WhatsApp por defecto
        alarm = env['calendar.alarm'].search([
            ('name', '=', 'WhatsApp - 1 Hora Antes'),
            ('alarm_type', '=', 'whatsapp')
        ])
        if not alarm:
            alarm = env['calendar.alarm'].create({
                'name': 'WhatsApp - 1 Hora Antes',
                'alarm_type': 'whatsapp',
                'duration': 1,
                'interval': 'hours',
                'whatsapp_template_id': calendar_template.id,
            })
            _logger.info("Alarma WhatsApp 'WhatsApp - 1 Hora Antes' creada (ID: %s)", alarm.id)

    _logger.info("WhatsApp templates y alarmas creados/verificados correctamente")
