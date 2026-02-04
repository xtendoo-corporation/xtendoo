import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    """Create default WhatsApp templates if a gateway exists."""
    gateway = env['mail.gateway'].search([('gateway_type', '=', 'whatsapp'), ('active', '=', True)], limit=1)
    if not gateway:
        _logger.warning("No WhatsApp gateway found. Skipping creation of default WhatsApp templates.")
        return

    booking_model = env.ref('xtendoo_booking_reserve.model_booking_request')

    # Approved Template
    values_approved = {
        'name': 'cita_aprobada_whatsapp',  # Minúsculas con guiones bajos
        'model_id': booking_model.id,
        'gateway_id': gateway.id,
        'category': 'utility',
        'language': 'es_ES',
        'status': 'approved',
        'body': 'Hola, su solicitud de cita ha sido APROBADA. Le esperamos.',
        'variable_ids': []
    }
    if not env['mail.whatsapp.template'].search([('name', '=', values_approved['name']), ('model_id', '=', values_approved['model_id'])]):
        env['mail.whatsapp.template'].create(values_approved)
        _logger.info("Template 'cita_aprobada_whatsapp' creado")

    # Rejected Template
    values_rejected = {
        'name': 'cita_rechazada_whatsapp',  # Minúsculas con guiones bajos
        'model_id': env.ref('xtendoo_booking_reserve.model_booking_request').id,
        'gateway_id': gateway.id,
        'category': 'utility',
        'language': 'es_ES',
        'status': 'approved',
        'body': 'Lamentamos informarle que su solicitud de cita ha sido RECHAZADA. Contacte con nosotros.',
        'variable_ids': []
    }
    if not env['mail.whatsapp.template'].search([('name', '=', values_rejected['name']), ('model_id', '=', values_rejected['model_id'])]):
        env['mail.whatsapp.template'].create(values_rejected)
        _logger.info("Template 'cita_rechazada_whatsapp' creado")

    # Template de Recordatorio para Calendar Event
    calendar_event_model = env['ir.model'].search([('model', '=', 'calendar.event')], limit=1)
    if calendar_event_model:
        values_calendar_reminder = {
            'name': 'recordatorio_cita_whatsapp',
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
            _logger.info("Template 'recordatorio_cita_whatsapp' creado para calendar.event (ID: %s)", calendar_template.id)
        else:
            _logger.info("Template 'recordatorio_cita_whatsapp' ya existe para calendar.event (ID: %s)", calendar_template.id)

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
