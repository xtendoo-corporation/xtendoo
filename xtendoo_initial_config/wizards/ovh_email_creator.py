# -*- coding: utf-8 -*-
import logging
import ovh
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Credenciales fijas para la API de OVH
OVH_APPLICATION_KEY = '9d14d317ec8e63c2'
OVH_APPLICATION_SECRET = '062157b0c4ca960674e23713a52cd835'

class OvhEmailCreator(models.TransientModel):
    _name = 'ovh.email.creator'
    _description = 'Wizard para crear correos electrónicos en OVH'

    application_key = fields.Char(string='Application Key', default=OVH_APPLICATION_KEY, readonly=True)
    application_secret = fields.Char(string='Application Secret', default=OVH_APPLICATION_SECRET, readonly=True)
    email_address = fields.Char(string='Dirección de correo', required=True,
                              help='Introduce solo la parte local (antes del @). El dominio se añadirá automáticamente.')
    password = fields.Char(string='Contraseña', required=True)
    domain = fields.Char(string='Dominio', required=True)
    endpoint = fields.Char(string='Endpoint OVH', default='ovh-eu', required=True)
    consumer_key = fields.Char(string='Consumer Key', readonly=True)
    validation_url = fields.Char(string='URL de validación', readonly=True)
    account_created = fields.Boolean(string='Cuenta creada', default=False)
    email_full = fields.Char(string='Email completo', compute='_compute_email_full', store=True)

    @api.depends('email_address', 'domain')
    def _compute_email_full(self):
        for record in self:
            if record.email_address and record.domain:
                record.email_full = f"{record.email_address}@{record.domain}"
            else:
                record.email_full = False

    @api.model
    def default_get(self, fields_list):
        result = super(OvhEmailCreator, self).default_get(fields_list)
        domain = self.env['ir.config_parameter'].sudo().get_param('xtendoo_initial_config.ovh_domain', '')
        endpoint = self.env['ir.config_parameter'].sudo().get_param('xtendoo_initial_config.ovh_endpoint', 'ovh-eu')
        consumer_key = self.env['ir.config_parameter'].sudo().get_param('xtendoo_initial_config.ovh_consumer_key', '')

        result['domain'] = domain
        result['endpoint'] = endpoint
        result['consumer_key'] = consumer_key
        return result

    @api.onchange('domain', 'endpoint')
    def _onchange_domain_endpoint(self):
        """Genera un nuevo consumer key si cambia el dominio o el endpoint y no hay uno ya definido"""
        if not self.consumer_key:
            self._generate_consumer_key()

    @api.model_create_multi
    def create(self, vals_list):
        """Override del método create con soporte para operaciones en batch"""
        records = super(OvhEmailCreator, self).create(vals_list)
        for record in records:
            if not record.consumer_key:
                record._generate_consumer_key()
        return records

    def _generate_consumer_key(self):
        """Genera un nuevo Consumer Key utilizando la API de OVH"""
        self.ensure_one()

        # Intentar obtener un consumer key existente primero
        consumer_key = self.env['ir.config_parameter'].sudo().get_param('xtendoo_initial_config.ovh_consumer_key', '')

        if consumer_key:
            self.consumer_key = consumer_key
            return

        # Si no hay consumer key existente, generarlo
        if self.endpoint:
            try:
                client = ovh.Client(
                    endpoint=self.endpoint,
                    application_key=OVH_APPLICATION_KEY,
                    application_secret=OVH_APPLICATION_SECRET
                )

                # Solicita un nuevo Consumer Key con permisos para gestionar correos
                ck = client.new_consumer_key_request()
                ck.add_rules(ovh.API_READ_WRITE, "/email/domain/*")

                # Realiza la solicitud
                validation = ck.request()

                # Almacena el Consumer Key y la URL de validación
                self.write({
                    'consumer_key': validation['consumerKey'],
                    'validation_url': validation['validationUrl']
                })

                # Guardar el Consumer Key en los parámetros del sistema
                self.env['ir.config_parameter'].sudo().set_param('xtendoo_initial_config.ovh_consumer_key', validation['consumerKey'])

                # Mostrar notificación al usuario
                self.env.user.notify_info(
                    message=_('Se ha generado un nuevo Consumer Key para OVH. Por favor, accede a la URL de validación para autorizar la aplicación.'),
                    title=_('Consumer Key generado'),
                    sticky=True
                )

            except ConnectionError as e:
                _logger.error("Error de conexión al generar el Consumer Key de OVH: %s", str(e))
                # No lanzamos excepción para que el wizard pueda abrirse
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _('No se pudo contactar con la API de OVH. Compruebe su conexión a Internet.'),
                        'type': 'warning',
                        'sticky': True,
                    }
                }
            except Exception as e:
                _logger.error("Error al generar el Consumer Key: %s", str(e))
                # No lanzamos excepción aquí para que el wizard pueda abrirse

    def _create_smtp_server(self, email_full):
        """Configura el servidor SMTP en Odoo usando la cuenta de correo creada"""
        try:
            # Comprobar si ya existe un servidor con el mismo nombre de usuario
            existing_server = self.env['ir.mail_server'].sudo().search([
                ('smtp_user', '=', email_full)
            ], limit=1)

            if existing_server:
                # Si ya existe un servidor con ese usuario, lo actualizamos
                existing_server.write({
                    'name': 'ovh',
                    'sequence': 10,
                    'smtp_host': 'ssl0.ovh.net',
                    'smtp_port': 465,
                    'smtp_encryption': 'ssl',
                    'smtp_user': email_full,
                    'smtp_pass': self.password,
                    'smtp_debug': True,
                })
                return existing_server
            else:
                # Si no existe, creamos uno nuevo
                smtp_server = self.env['ir.mail_server'].sudo().create({
                    'name': 'ovh',
                    'sequence': 10,
                    'smtp_host': 'ssl0.ovh.net',
                    'smtp_port': 465,
                    'smtp_encryption': 'ssl',
                    'smtp_user': email_full,
                    'smtp_pass': self.password,
                    'smtp_debug': True,
                })
                return smtp_server
        except Exception as e:
            _logger.error("Error al configurar el servidor SMTP: %s", str(e))
            raise UserError(_("La cuenta de correo se creó correctamente en OVH, pero ocurrió un error al configurar el servidor SMTP en Odoo: %s") % str(e))

    def _configure_fetchmail_server(self, email_full):
        """Configura el servidor de entrada IMAP en Odoo usando la cuenta de correo creada"""
        try:
            # Comprobar si ya existe un servidor con el mismo nombre de usuario
            existing_server = self.env['fetchmail.server'].sudo().search([
                ('user', '=', email_full)
            ], limit=1)

            if existing_server:
                # Si ya existe un servidor con ese usuario, lo actualizamos
                existing_server.write({
                    'name': 'ovh',
                    'priority': 10,
                    'server': 'ssl0.ovh.net',
                    'port': 993,
                    'server_type': 'imap',
                    'is_ssl': True,
                    'user': email_full,
                    'password': self.password,
                    'state': 'draft',
                })
                return existing_server
            else:
                # Si no existe, creamos uno nuevo
                fetchmail_server = self.env['fetchmail.server'].sudo().create({
                    'name': 'ovh',
                    'priority': 10,
                    'server': 'ssl0.ovh.net',
                    'port': 993,
                    'server_type': 'imap',
                    'is_ssl': True,
                    'user': email_full,
                    'password': self.password,
                    'state': 'draft',
                })
                return fetchmail_server
        except Exception as e:
            _logger.error("Error al configurar el servidor de correo entrante: %s", str(e))
            raise UserError(_("La cuenta de correo se creó correctamente en OVH, pero ocurrió un error al configurar el servidor de correo entrante en Odoo: %s") % str(e))

    def _configure_mail_alias_domain(self, email_full):
        """Configura el dominio de alias para el sistema de correo de Odoo"""
        try:
            # Extraer el dominio del email completo
            domain = self.domain

            # Comprobar si ya existe un registro para este dominio
            existing_domain = self.env['mail.alias.domain'].sudo().search([
                ('name', '=', domain)
            ], limit=1)

            if existing_domain:
                # Si ya existe, lo actualizamos
                existing_domain.write({
                    'bounce_alias': 'bounce',
                    'catchall_alias': self.email_address,
                    'default_from_alias': self.email_address,
                })
                return existing_domain
            else:
                # Si no existe, lo creamos
                alias_domain = self.env['mail.alias.domain'].sudo().create({
                    'name': domain,
                    'bounce_alias': 'bounce',
                    'catchall_alias': self.email_address,
                    'default_from_alias': self.email_address,
                })
                return alias_domain
        except Exception as e:
            _logger.error("Error al configurar el dominio de alias de correo: %s", str(e))
            raise UserError(_("Ocurrió un error al configurar el dominio de alias de correo: %s") % str(e))

    def action_create_email(self):
        """Crear una cuenta de correo en OVH usando la API"""
        # Generar consumer key si no existe
        if not self.consumer_key:
            result = self._generate_consumer_key()
            if isinstance(result, dict) and result.get('tag') == 'display_notification':
                return result

        # Validar que tenemos toda la información necesaria
        if not all([self.endpoint, self.consumer_key, self.domain]):
            raise UserError(_("No se pudo generar un Consumer Key válido. Por favor, contacte al administrador."))

        if not self.email_address or not self.password:
            raise UserError(_("Por favor, introduzca una dirección de correo y una contraseña"))

        try:
            # Inicializar el cliente OVH con las credenciales fijas y el consumer key
            client = ovh.Client(
                endpoint=self.endpoint,
                application_key=OVH_APPLICATION_KEY,
                application_secret=OVH_APPLICATION_SECRET,
                consumer_key=self.consumer_key
            )

            # Crear la cuenta de correo
            email_full = f"{self.email_address}@{self.domain}"

            try:
                # Verificar si la cuenta ya existe
                client.get(f'/email/domain/{self.domain}/account/{self.email_address}')
                raise UserError(_("La cuenta de correo %s ya existe") % email_full)
            except ovh.exceptions.ResourceNotFoundError:
                # La cuenta no existe, podemos crearla
                pass
            except ConnectionError as e:
                _logger.error("Error de conexión al verificar la cuenta de correo: %s", str(e))
                raise UserError(_("No se pudo contactar con la API de OVH. Compruebe su conexión a Internet."))

            try:
                # Crear la cuenta
                # OVH tiene una limitación en el tamaño de la descripción - limitamos a 20 caracteres
                description = f'Creada desde Odoo'
                client.post(
                    f'/email/domain/{self.domain}/account',
                    accountName=self.email_address,
                    password=self.password,
                    description=description
                )
            except ConnectionError as e:
                _logger.error("Error de conexión al crear la cuenta de correo: %s", str(e))
                raise UserError(_("No se pudo contactar con la API de OVH. Compruebe su conexión a Internet."))

            # Guardar los valores en los parámetros del sistema para futuros usos
            self.env['ir.config_parameter'].sudo().set_param('xtendoo_initial_config.ovh_domain', self.domain)
            self.env['ir.config_parameter'].sudo().set_param('xtendoo_initial_config.ovh_endpoint', self.endpoint)

            # Marcar la cuenta como creada
            self.write({
                'account_created': True,
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('La cuenta de correo %s se ha creado correctamente') % email_full,
                    'type': 'success',
                    'sticky': False,
                }
            }

        except ovh.exceptions.APIError as e:
            _logger.error("Error de la API de OVH: %s", str(e))
            raise UserError(_("Error al crear la cuenta de correo: %s") % str(e))
        except Exception as e:
            _logger.error("Error inesperado: %s", str(e))
            raise UserError(_("Error inesperado: %s") % str(e))

    def action_configure_mail_servers(self):
        """Configura los servidores de correo entrante y saliente en Odoo"""
        if not self.email_full:
            raise UserError(_("Por favor, complete los campos de dirección de correo y dominio"))

        try:
            # Configurar servidor SMTP
            smtp_server = self._create_smtp_server(self.email_full)

            # Configurar servidor de correo entrante
            fetchmail_server = self._configure_fetchmail_server(self.email_full)

            # Configurar el dominio de alias
            alias_domain = self._configure_mail_alias_domain(self.email_full)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Los servidores de correo y el dominio de alias para %s han sido configurados correctamente') % self.email_full,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error("Error al configurar los servidores de correo: %s", str(e))
            raise UserError(_("Error al configurar los servidores de correo: %s") % str(e))
