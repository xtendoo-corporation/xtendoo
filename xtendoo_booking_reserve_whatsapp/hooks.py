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
        (0, 0, {'name': '{{var_1}}', 'line_type': 'body', 'field_type': 'field', 'field_name': 'name', 'demo_value': 'Juan Pérez'}),
        (0, 0, {'name': '{{var_2}}', 'line_type': 'body', 'field_type': 'field', 'field_name': 'booking_date', 'demo_value': '2023-10-25'}),
        (0, 0, {'name': '{{var_3}}', 'line_type': 'body', 'field_type': 'field', 'field_name': 'booking_hour', 'demo_value': '10:00'}),
    ]

    # Reminder Template
    values_reminder = {
        'name': 'Recordatorio Cita WhatsApp',
        'model_id': env.ref('xtendoo_booking_reserve.model_booking_request').id,
        'gateway_id': gateway.id,
        'body': 'Hola {{var_1}}, le recordamos su cita para el {{var_2}} a las {{var_3}}. ¡Gracias!',
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
        'body': 'Hola {{var_1}}, su solicitud de cita para el {{var_2}} a las {{var_3}} ha sido APROBADA. Le esperamos.',
        'variable_ids': [(0, 0, v[2]) for v in variables] # Recreate to avoid sharing ORM stack issues if any validation checks ids
    }
    if not env['mail.whatsapp.template'].search([('name', '=', values_approved['name']), ('model_id', '=', values_approved['model_id'])]):
        env['mail.whatsapp.template'].create(values_approved)

    # Rejected Template
    values_rejected = {
        'name': 'Cita Rechazada WhatsApp',
        'model_id': env.ref('xtendoo_booking_reserve.model_booking_request').id,
        'gateway_id': gateway.id,
        'body': 'Hola {{var_1}}, lamentamos informarle que su solicitud de cita para el {{var_2}} a las {{var_3}} ha sido RECHAZADA. Contacte con nosotros.',
        'variable_ids': [(0, 0, v[2]) for v in variables]
    }
    if not env['mail.whatsapp.template'].search([('name', '=', values_rejected['name']), ('model_id', '=', values_rejected['model_id'])]):
        env['mail.whatsapp.template'].create(values_rejected)

