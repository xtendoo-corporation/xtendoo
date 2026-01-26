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
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Solo se pueden aprobar solicitudes pendientes.'))
        
        # Create or find partner
        partner = self._get_or_create_partner()
        
        # Create resource.booking
        booking = self._create_booking(partner)
        
        # Update request state
        self.write({
            'state': 'approved',
            'booking_id': booking.id,
            'partner_id': partner.id,
        })
        
        # Post message in chatter
        # Post message in chatter (Internal Note)
        self.message_post(
            body=_('Solicitud aprobada. Reserva creada: <a href="#" data-oe-model="resource.booking" data-oe-id="%s">%s</a>') % (booking.id, booking.display_name),
            subtype_xmlid='mail.mt_note'
        )
        
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
        
        self.write({'state': 'rejected'})
        
        # Post message in chatter
        # Post message in chatter (Internal Note)
        self.message_post(
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
        # Parse booking datetime
        booking_datetime = self._parse_booking_datetime()
        
        # Calculate duration from type
        duration = self.type_id.duration or 0.5
        
        # Prepare booking values
        booking_vals = {
            'type_id': self.type_id.id,
            'partner_ids': [(6, 0, [partner.id])],
            'name': _('Reserva web: %s') % self.name,
            'start': booking_datetime,
            'duration': duration,
            'combination_auto_assign': True,
        }
        
        # Create booking
        booking = self.env['resource.booking'].sudo().create(booking_vals)
        
        return booking

    def _parse_booking_datetime(self):
        """Convert booking_date and booking_hour to datetime"""
        # Parse hour (format: "HH:MM")
        try:
            hour_parts = self.booking_hour.split(':')
            hour = int(hour_parts[0])
            minute = int(hour_parts[1]) if len(hour_parts) > 1 else 0
        except (ValueError, IndexError):
            raise UserError(_('Formato de hora inválido: %s') % self.booking_hour)
        
        # Combine date and time
        booking_datetime = datetime.combine(
            self.booking_date,
            datetime.min.time().replace(hour=hour, minute=minute)
        )
        
        return booking_datetime

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
