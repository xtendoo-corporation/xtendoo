# Copyright 2026 Xtendoo
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class BookingRequest(models.Model):
    _name = 'booking.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Booking Request'
    _order = 'create_date desc'

    name = fields.Char(
        string='Nombre',
        required=True,
        tracking=True,
        help="Nombre del solicitante"
    )
    phone = fields.Char(
        string='Teléfono',
        required=True,
        tracking=True,
        help="Teléfono de contacto"
    )
    email = fields.Char(
        string='Email',
        tracking=True,
        help="Email del solicitante"
    )
    type_id = fields.Many2one(
        comodel_name='resource.booking.type',
        string='Tipo de Cita',
        required=True,
        tracking=True,
        ondelete='restrict'
    )
    booking_date = fields.Date(
        string='Fecha',
        required=True,
        tracking=True,
        help="Fecha de la reserva solicitada"
    )
    booking_hour = fields.Char(
        string='Hora',
        required=True,
        tracking=True,
        help="Hora de la reserva (formato HH:MM)"
    )
    state = fields.Selection(
        selection=[
            ('pending', 'Pendiente'),
            ('approved', 'Aprobada'),
            ('rejected', 'Rechazada')
        ],
        string='Estado',
        default='pending',
        required=True,
        tracking=True,
        help="Estado de la solicitud de reserva"
    )
    booking_id = fields.Many2one(
        comodel_name='resource.booking',
        string='Reserva Creada',
        readonly=True,
        help="Reserva creada al aprobar la solicitud"
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        help="Partner asociado (se crea automáticamente si no existe)"
    )
    notes = fields.Text(
        string='Notas',
        help="Notas adicionales sobre la solicitud"
    )

    def action_approve(self):
        """Approve the booking request and create a resource.booking"""
        import logging
        _logger = logging.getLogger(__name__)

        self.ensure_one()
        _logger.info("=" * 80)
        _logger.info("INICIO action_approve() para solicitud ID: %s", self.id)
        _logger.info("Nombre: %s, Email: %s, Teléfono: %s", self.name, self.email, self.phone)
        _logger.info("Fecha: %s, Hora: %s", self.booking_date, self.booking_hour)
        _logger.info("=" * 80)

        if self.state != 'pending':
            raise UserError(_('Solo se pueden aprobar solicitudes pendientes.'))

        # Create or find partner
        _logger.info("→ Buscando/creando partner...")
        partner = self._get_or_create_partner()
        _logger.info("✓ Partner encontrado/creado: %s (ID: %s, Email: %s)", partner.name, partner.id, partner.email)

        # Create resource.booking
        _logger.info("→ Creando resource.booking...")
        _logger.info("   Contexto ANTES de crear booking: %s", self.env.context)
        booking = self._create_booking(partner)
        _logger.info("✓ Booking creado: ID %s", booking.id)
        _logger.info("   Start: %s, Stop: %s", booking.start, booking.stop)

        # Update request state - Desactivar tracking para evitar emails automáticos
        _logger.info("→ Actualizando estado de solicitud a 'approved'...")
        _logger.info("   Contexto: mail_notrack=True, mail_create_nolog=True")
        self.with_context(mail_notrack=True, mail_create_nolog=True).write({
            'state': 'approved',
            'booking_id': booking.id,
            'partner_id': partner.id,
        })
        _logger.info("✓ Estado actualizado")

        # Post message in chatter (Internal Note) - Sin notificar
        _logger.info("→ Publicando mensaje en chatter (nota interna)...")
        self.with_context(mail_notrack=True).message_post(
            body=_('Solicitud aprobada. Reserva creada: <a href="#" data-oe-model="resource.booking" data-oe-id="%s">%s</a>') % (booking.id, booking.display_name),
            subtype_xmlid='mail.mt_note'
        )
        _logger.info("✓ Mensaje publicado")
        _logger.info("=" * 80)
        _logger.info("FIN action_approve()")
        _logger.info("=" * 80)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('¡Aprobada!'),
                'message': _('La solicitud ha sido aprobada y se ha creado la reserva.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reject(self):
        """Reject the booking request"""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Solo se pueden rechazar solicitudes pendientes.'))

        # Desactivar tracking para evitar emails automáticos
        self.with_context(mail_notrack=True, mail_create_nolog=True).write({'state': 'rejected'})

        # Post message in chatter (Internal Note) - Sin notificar
        self.with_context(mail_notrack=True).message_post(
            body=_('Solicitud rechazada'),
            subtype_xmlid='mail.mt_note'
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Rechazada'),
                'message': _('La solicitud ha sido rechazada.'),
                'type': 'warning',
                'sticky': False,
            }
        }

    def _get_or_create_partner(self):
        """Get or create partner from request data"""
        Partner = self.env['res.partner'].sudo()

        # Try to find existing partner by email
        if self.email:
            partner = Partner.search([('email', '=', self.email)], limit=1)
            if partner:
                return partner

        # Create new partner
        partner_vals = {
            'name': self.name,
            'phone': self.phone,
            'email': self.email or False,
        }
        return Partner.create(partner_vals)

    def _create_booking(self, partner):
        """Create resource.booking from request"""
        import logging
        _logger = logging.getLogger(__name__)

        _logger.info("   ┌─ _create_booking() INICIO")
        _logger.info("   │  Partner: %s (ID: %s)", partner.name, partner.id)

        # Parse booking datetime
        _logger.info("   │  → Parseando fecha y hora...")
        _logger.info("   │     booking_date: %s", self.booking_date)
        _logger.info("   │     booking_hour: %s", self.booking_hour)
        booking_datetime = self._parse_booking_datetime()
        _logger.info("   │  ✓ DateTime parseado: %s", booking_datetime)
        _logger.info("   │     (Tipo: %s, Timezone: %s)", type(booking_datetime), booking_datetime.tzinfo)

        # Calculate duration from type
        duration = self.type_id.duration or 0.5
        _logger.info("   │  ✓ Duración: %s horas", duration)

        # Prepare booking values
        booking_vals = {
            'type_id': self.type_id.id,
            'partner_ids': [(6, 0, [partner.id])],
            'name': _('Reserva web: %s') % self.name,
            'start': booking_datetime,
            'duration': duration,
            'combination_auto_assign': True,
        }
        _logger.info("   │  ✓ Valores de booking preparados:")
        _logger.info("   │     - type_id: %s", booking_vals['type_id'])
        _logger.info("   │     - name: %s", booking_vals['name'])
        _logger.info("   │     - start: %s", booking_vals['start'])
        _logger.info("   │     - duration: %s", booking_vals['duration'])
        _logger.info("   │     - partner_ids: %s", booking_vals['partner_ids'])

        # Create booking - Desactivar TODAS las notificaciones automáticas
        _logger.info("   │  → Creando resource.booking con contexto:")
        _logger.info("   │     mail_create_nosubscribe=True")
        _logger.info("   │     mail_create_nolog=True")
        _logger.info("   │     mail_notrack=True")
        _logger.info("   │     tracking_disable=True")

        booking = self.env['resource.booking'].with_context(
            mail_create_nosubscribe=True,  # No suscribir partners automáticamente
            mail_create_nolog=True,  # No crear logs
            mail_notrack=True,  # No enviar tracking
            tracking_disable=True,  # Desactivar tracking completamente
        ).sudo().create(booking_vals)

        _logger.info("   │  ✓ Booking creado: ID %s", booking.id)
        _logger.info("   │     - Start guardado: %s", booking.start)
        _logger.info("   │     - Stop guardado: %s", booking.stop)
        _logger.info("   └─ _create_booking() FIN")

        return booking

    def _parse_booking_datetime(self):
        """Convert booking_date and booking_hour to datetime with timezone handling"""
        from pytz import timezone as pytz_timezone
        import logging
        _logger = logging.getLogger(__name__)

        _logger.info("      ┌─ _parse_booking_datetime() INICIO")

        # Parse hour (format: "HH:MM")
        try:
            hour_parts = self.booking_hour.split(':')
            hour = int(hour_parts[0])
            minute = int(hour_parts[1]) if len(hour_parts) > 1 else 0
            _logger.info("      │  ✓ Hora parseada: %02d:%02d", hour, minute)
        except (ValueError, IndexError):
            raise UserError(_('Formato de hora inválido: %s') % self.booking_hour)

        # Get user timezone or company timezone
        user_tz = self.env.user.tz or self.env.company.partner_id.tz or 'UTC'
        _logger.info("      │  → Timezone del usuario: %s", user_tz)
        _logger.info("      │     (env.user.tz: %s)", self.env.user.tz)
        _logger.info("      │     (company tz: %s)", self.env.company.partner_id.tz)
        tz = pytz_timezone(user_tz)

        # Combine date and time in user's timezone
        local_dt = datetime.combine(
            self.booking_date,
            datetime.min.time().replace(hour=hour, minute=minute)
        )
        _logger.info("      │  ✓ DateTime local (naive): %s", local_dt)

        # Localize to user timezone and convert to UTC (Odoo stores in UTC)
        local_dt = tz.localize(local_dt)
        _logger.info("      │  ✓ DateTime localizado a %s: %s", user_tz, local_dt)

        booking_datetime_utc = local_dt.astimezone(pytz_timezone('UTC'))
        _logger.info("      │  ✓ DateTime convertido a UTC: %s", booking_datetime_utc)

        # Return naive datetime in UTC (as Odoo expects)
        result = booking_datetime_utc.replace(tzinfo=None)
        _logger.info("      │  ✓ DateTime final (naive UTC): %s", result)
        _logger.info("      └─ _parse_booking_datetime() FIN")

        return result

    @api.model
    def create(self, vals):
        """Override create to send notification"""
        result = super().create(vals)

        # Notify admins about new request
        result._notify_new_request()

        return result

    def _notify_new_request(self):
        """Send notification to booking managers"""
        # Find users with booking manager group
        group = self.env.ref('resource_booking.group_manager', raise_if_not_found=False)
        if not group:
            return

        # Create activity for managers
        for user in group.users:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=_('Nueva solicitud de reserva'),
                note=_('Se ha recibido una nueva solicitud de reserva de %s para el %s a las %s') % (
                    self.name,
                    self.booking_date,
                    self.booking_hour
                )
            )
