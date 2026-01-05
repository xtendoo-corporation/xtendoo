# Copyright 2024 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class WhatsappPendingConfirmation(models.Model):
    _name = 'whatsapp.pending.confirmation'
    _description = 'WhatsApp Confirmaciones Pendientes'
    _order = 'sent_date desc'

    partner_id = fields.Many2one(
        'res.partner',
        string="Cliente",
        required=True,
        ondelete='cascade',
        index=True
    )
    channel_id = fields.Many2one(
        'discuss.channel',
        string="Canal WhatsApp",
        required=True,
        ondelete='cascade',
        index=True
    )
    template_id = fields.Many2one(
        'mail.whatsapp.template',
        string="Plantilla Original",
        required=True,
        ondelete='cascade'
    )
    confirmation_template_id = fields.Many2one(
        'mail.whatsapp.template',
        string="Plantilla de Confirmación",
        required=True,
        ondelete='cascade'
    )
    res_model = fields.Char(
        string="Modelo",
        required=True,
        help="Modelo del registro relacionado (ej: sale.order, account.move)"
    )
    res_id = fields.Integer(
        string="ID del Registro",
        required=True,
        help="ID del registro relacionado"
    )
    state = fields.Selection([
        ('waiting', 'Esperando Confirmación'),
        ('confirmed', 'Confirmado'),
        ('expired', 'Expirado'),
        ('cancelled', 'Cancelado')
    ], default='waiting', required=True, index=True)

    sent_date = fields.Datetime(
        string="Fecha de Envío",
        default=fields.Datetime.now,
        required=True
    )
    response_date = fields.Datetime(
        string="Fecha de Respuesta",
        readonly=True
    )
    confirmation_type = fields.Selection([
        ('button', 'Botón Interactivo'),
        ('text_si', 'Texto: Sí'),
        ('text_ok', 'Texto: OK'),
        ('any', 'Cualquier Respuesta')
    ], string="Tipo de Confirmación Esperada", required=True)

    expiry_date = fields.Datetime(
        string="Fecha de Expiración",
        compute='_compute_expiry_date',
        store=True,
        help="Las confirmaciones expiran después de 24 horas"
    )

    notes = fields.Text(string="Notas")

    @api.depends('sent_date')
    def _compute_expiry_date(self):
        """Las confirmaciones expiran 24 horas después del envío"""
        for record in self:
            if record.sent_date:
                record.expiry_date = record.sent_date + timedelta(hours=24)
            else:
                record.expiry_date = False

    @api.model
    def _cron_expire_pending_confirmations(self):
        """
        Cron job para marcar como expiradas las confirmaciones pendientes
        después de 24 horas.
        """
        now = fields.Datetime.now()
        expired = self.search([
            ('state', '=', 'waiting'),
            ('expiry_date', '<', now)
        ])

        if expired:
            expired.write({'state': 'expired'})
            _logger.info(f"Expired {len(expired)} pending WhatsApp confirmations")

        return True

    def process_confirmation_response(self, message_data):
        """
        Procesa una respuesta del cliente y envía la plantilla de confirmación si corresponde.

        :param message_data: Datos del mensaje recibido desde WhatsApp
        :return: True si se procesó correctamente, False si no
        """
        self.ensure_one()

        if self.state != 'waiting':
            _logger.info(f"❌ Confirmation {self.id} already processed (state: {self.state})")
            return False

        # Verificar si la confirmación ha expirado
        if self.expiry_date and fields.Datetime.now() > self.expiry_date:
            _logger.info(f"❌ Confirmation {self.id} has expired")
            self.state = 'expired'
            return False

        confirmed = self._check_if_confirmed(message_data)

        if confirmed:
            _logger.info(f"✅ Confirmation {self.id} received from partner {self.partner_id.name}")
            self.write({
                'state': 'confirmed',
                'response_date': fields.Datetime.now()
            })

            # Enviar la plantilla de confirmación
            self._send_confirmation_template()
            return True
        else:
            _logger.info(f"⚠️ Message received but does not match confirmation criteria for {self.id}")
            return False

    def _check_if_confirmed(self, message_data):
        """
        Verifica si el mensaje recibido es una confirmación válida.

        :param message_data: Datos del mensaje desde WhatsApp
        :return: True si es una confirmación válida
        """
        self.ensure_one()

        message_type = message_data.get('type', '')

        _logger.info(f"🔍 Checking confirmation for pending {self.id}")
        _logger.info(f"   📋 Confirmation type expected: {self.confirmation_type}")
        _logger.info(f"   📨 Message type received: {message_type}")
        _logger.info(f"   📦 Full message_data: {message_data}")

        if self.confirmation_type == 'button':
            # Cualquier respuesta de botón interactivo cuenta como confirmación
            if message_type == 'interactive':
                _logger.info(f"   ✅ Match! Interactive button detected")
                return True
            else:
                _logger.info(f"   ❌ No match: Expected interactive, got {message_type}")

        elif self.confirmation_type == 'text_si':
            # Buscar "si" o "sí" en el texto O en botones interactivos
            if message_type == 'text':
                text = message_data.get('text', {}).get('body', '').strip().lower()
                _logger.info(f"   📝 Text received: '{text}'")
                if text in ['si', 'sí', 's', 'yes', 'y']:
                    _logger.info(f"   ✅ Match! Text is a confirmation")
                    return True
                else:
                    _logger.info(f"   ❌ No match: Text not in confirmation list")
            elif message_type == 'interactive':
                # También aceptar botones interactivos con texto "Si"
                button_text = message_data.get('interactive', {}).get('button_reply', {}).get('title', '').strip().lower()
                _logger.info(f"   🔘 Button text received: '{button_text}'")
                if button_text in ['si', 'sí', 's', 'yes', 'y']:
                    _logger.info(f"   ✅ Match! Button text is a confirmation")
                    return True
                else:
                    _logger.info(f"   ❌ No match: Button text not in confirmation list")

        elif self.confirmation_type == 'text_ok':
            # Buscar "ok" en el texto O en botones interactivos
            if message_type == 'text':
                text = message_data.get('text', {}).get('body', '').strip().lower()
                _logger.info(f"   📝 Text received: '{text}'")
                if text in ['ok', 'vale', 'okay', 'k']:
                    _logger.info(f"   ✅ Match! Text is a confirmation")
                    return True
                else:
                    _logger.info(f"   ❌ No match: Text not in confirmation list")
            elif message_type == 'interactive':
                # También aceptar botones interactivos con texto "OK"
                button_text = message_data.get('interactive', {}).get('button_reply', {}).get('title', '').strip().lower()
                _logger.info(f"   🔘 Button text received: '{button_text}'")
                if button_text in ['ok', 'vale', 'okay', 'k']:
                    _logger.info(f"   ✅ Match! Button text is a confirmation")
                    return True
                else:
                    _logger.info(f"   ❌ No match: Button text not in confirmation list")

        elif self.confirmation_type == 'any':
            # Cualquier tipo de respuesta cuenta
            _logger.info(f"   ✅ Match! 'any' type accepts all responses")
            return True

        return False

    def _send_confirmation_template(self):
        """
        Envía la plantilla de confirmación configurada.
        """
        self.ensure_one()

        if not self.confirmation_template_id:
            _logger.warning(f"⚠️ No confirmation template configured for pending confirmation {self.id}")
            return False

        try:
            # Obtener el registro relacionado
            record = self.env[self.res_model].browse(self.res_id)
            if not record.exists():
                _logger.error(f"❌ Record {self.res_model} #{self.res_id} no longer exists")
                return False

            _logger.info(f"📨 Sending confirmation template '{self.confirmation_template_id.name}' to {self.partner_id.name}")

            # Crear el composer para enviar la plantilla
            composer = self.env['whatsapp.composer'].with_context(
                active_model=self.res_model,
                active_id=self.res_id,
                default_res_model=self.res_model,
                default_res_id=self.res_id,
            ).create({
                'res_model': self.res_model,
                'res_id': self.res_id,
                'template_id': self.confirmation_template_id.id,
            })

            # Ejecutar onchange para que se completen los datos desde la plantilla
            composer.onchange_template_id()

            # Si aún no hay body, obtenerlo de la plantilla
            if not composer.body and self.confirmation_template_id.body:
                composer.body = self.confirmation_template_id.body

            _logger.info(f"📋 Composer created with body: {composer.body[:50] if composer.body else 'EMPTY'}...")

            # Enviar el mensaje
            composer.action_send_whatsapp()

            _logger.info(f"✅ Confirmation template sent successfully for record {self.res_model} #{self.res_id}")

            # Añadir nota al registro
            record.message_post(
                body=_("Plantilla de confirmación de WhatsApp enviada automáticamente: %s") % self.confirmation_template_id.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )

            return True

        except Exception as e:
            _logger.error(f"❌ Error sending confirmation template: {e}", exc_info=True)
            self.notes = f"Error al enviar plantilla: {str(e)}"
            return False

