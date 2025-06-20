# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class OvhEmailCreator(models.TransientModel):
    _name = 'ovh.email.creator'
    _description = 'Wizard para crear correos electrónicos en OVH'

    email_address = fields.Char(string='Dirección de correo', required=True,
                              help='Introduce solo la parte local (antes del @). El dominio se añadirá automáticamente.')
    password = fields.Char(string='Contraseña', required=True)
    domain = fields.Char(string='Dominio', required=True)
    email_full = fields.Char(string='Email completo', compute='_compute_email_full', store=True)
    consumer_key = fields.Char(string='Consumer Key', help='Clave de acceso a la API de OVH')

    @api.depends('email_address', 'domain')
    def _compute_email_full(self):
        for record in self:
            if record.email_address and record.domain:
                record.email_full = f"{record.email_address}@{record.domain}"
            else:
                record.email_full = False

    @api.model_create_multi
    def create(self, vals_list):
        """Override del método create con soporte para operaciones en batch"""
        records = super(OvhEmailCreator, self).create(vals_list)
        for record in records:
            if not record.consumer_key:
                record._generate_consumer_key()
        return records

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
                    'default_from': self.email_address,
                })
                return existing_domain
            else:
                # Si no existe, lo creamos
                alias_domain = self.env['mail.alias.domain'].sudo().create({
                    'name': domain,
                    'bounce_alias': 'bounce',
                    'catchall_alias': self.email_address,
                    'default_from': self.email_address,
                })
                return alias_domain
        except Exception as e:
            _logger.error("Error al configurar el dominio de alias de correo: %s", str(e))
            raise UserError(_("Ocurrió un error al configurar el dominio de alias de correo: %s") % str(e))

    def _set_spanish_language_for_all(self):
        """Establece el idioma español para todos los usuarios, activos e inactivos"""
        spanish_lang = self.env['res.lang'].search([('code', '=', 'es_ES')])
        if spanish_lang:
            # Cambiar el idioma para todos los usuarios (activos e inactivos)
            users = self.env['res.users'].with_context(active_test=False).search([])
            users.write({'lang': 'es_ES'})

            # Cambiar el idioma para todos los partners/contactos (activos e inactivos)
            partners = self.env['res.partner'].with_context(active_test=False).search([])
            partners.write({'lang': 'es_ES'})

    def _activate_multi_warehouse_and_location(self):
        """Activa el modo multialmacén y multiubicación en Odoo"""
        try:
            # Obtener la configuración actual
            IrConfigParameter = self.env['ir.config_parameter'].sudo()

            # Buscar el grupo de multialmacenes
            group_stock_multi_warehouses = self.env.ref('stock.group_stock_multi_warehouses', raise_if_not_found=False)
            if group_stock_multi_warehouses:
                # Asignar a todos los usuarios en el grupo base.group_user
                base_user_group = self.env.ref('base.group_user')
                if base_user_group:
                    base_user_group.write({'implied_ids': [(4, group_stock_multi_warehouses.id)]})

            # Buscar el grupo de multiubicaciones
            group_stock_multi_locations = self.env.ref('stock.group_stock_multi_locations', raise_if_not_found=False)
            if group_stock_multi_locations:
                # Asignar a todos los usuarios en el grupo base.group_user
                base_user_group = self.env.ref('base.group_user')
                if base_user_group:
                    base_user_group.write({'implied_ids': [(4, group_stock_multi_locations.id)]})

            _logger.info("Configuración de multialmacén y multiubicación activada con éxito")
        except Exception as e:
            _logger.error("Error al activar multialmacén y multiubicación: %s", str(e))
            raise UserError(_("Error al activar multialmacén y multiubicación: %s") % str(e))

    def _translate_default_stock_locations(self):
        """Traduce los nombres de ubicaciones y rutas por defecto de Odoo al español"""
        location_map = {
            'Physical Locations': 'Ubicaciones Físicas',
            'Partners': 'Socios',
            'Virtual Locations': 'Ubicaciones Virtuales',
            'Vendors': 'Proveedores',
            'Customers': 'Clientes',
            'Inter-company transit': 'Tránsito entre compañías',
        }
        for eng, esp in location_map.items():
            locations = self.env['stock.location'].search([('name', '=', eng)])
            locations.write({'name': esp})

        # Traducir la ruta MTO
        route = self.env['stock.route'].search([('name', '=', 'Replenish on Order (MTO)')])
        if route:
            route.write({'name': 'Reabastecer bajo pedido (MTO)'})

    def _update_sale_order_sequence(self):
        """Actualiza la secuencia de pedidos de venta"""
        seq = self.env['ir.sequence'].search([('code', '=', 'sale.order')], limit=1)
        if seq:
            seq.write({
                'prefix': 'VTA/%(year)s/',
                'use_date_range': True,
            })

    def _update_purchase_order_sequence(self):
        """Actualiza la secuencia de pedidos de compra"""
        seq = self.env['ir.sequence'].search([('code', '=', 'purchase.order')], limit=1)
        if seq:
            seq.write({
                'prefix': 'COM/%(year)s/',
                'use_date_range': True,
            })

    def _update_invoice_sequence(self):
        """Actualiza la secuencia de facturas"""
        seq = self.env['ir.sequence'].search([('code', '=', 'account.move')], limit=1)
        if seq:
            seq.write({
                'prefix': 'FAC/%(year)s/',
                'use_date_range': True,
            })

    def _deactivate_english_language(self):
        """Desactiva el idioma inglés"""
        messages = []
        try:
            english_lang = self.env['res.lang'].search([('code', '=', 'en_US')])
            if english_lang:
                if self.env['ir.config_parameter'].get_param('base.lang_default') != 'en_US':
                    english_lang.active = False
                    messages.append(_("Idioma inglés desactivado."))
                else:
                    messages.append(_("Idioma inglés no desactivado por ser el idioma predeterminado."))
        except Exception as e:
            self.env.cr.rollback()
            messages.append(_("Error al desactivar el idioma inglés: %s") % str(e))

        return messages

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

            self._set_spanish_language_for_all()

            self._activate_multi_warehouse_and_location()

            self._translate_default_stock_locations()

            self._update_sale_order_sequence()

            self._update_purchase_order_sequence()

            self._update_invoice_sequence()

            self._deactivate_english_language()

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
