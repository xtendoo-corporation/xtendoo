# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json

class XtendooConfigWizard(models.TransientModel):
    _name = 'xtendoo.config.wizard'
    _description = 'Asistente de Configuración Inicial Xtendoo'

    summary = fields.Text(string="Resumen de Cambios", readonly=True)

    def action_apply_config(self):
        messages = []
        env = self.env

        # Instalación de módulos requeridos
        messages.extend(self._install_required_modules())

        # Resumen
        self.summary = "\n".join(messages)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'xtendoo.config.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_start_spanish_tour(self):
        """Inicia el tour interactivo para activar el idioma español"""
        return {
            'type': 'ir.actions.client',
            'tag': 'xtendoo_activate_spanish_tour',
            'params': {},
            'target': 'main',
        }

    def _install_required_modules(self):
        """Instala los módulos requeridos"""
        messages = []
        installed_modules = self.env['ir.module.module'].search([('state', '=', 'installed')]).mapped('name')

        for module in ['l10n_es_toponyms', 'web_responsive', 'contacts', 'stock']:
            if module == 'web_responsive' and 'web_enterprise' in installed_modules:
                messages.append(_("Módulo web_responsive no instalado por conflicto con web_enterprise."))
                continue  # Saltar instalación si web_enterprise está instalado

            mod = self.env['ir.module.module'].search([('name', '=', module)])
            if mod and mod.state != 'installed':
                mod.button_install()
                messages.append(_("Módulo %s marcado para instalación.") % module)
            else:
                messages.append(_("Módulo %s ya instalado o no disponible.") % module)

        return messages

    def _set_spanish_language_for_all(self):
        """Establece el idioma español para todos los usuarios"""
        spanish_lang = self.env['res.lang'].search([('code', '=', 'es_ES')])
        if spanish_lang:
            # Cambiar el idioma para todos los usuarios
            users = self.env['res.users'].search([])
            users.write({'lang': 'es_ES'})

            # Cambiar el idioma para todos los partners/contactos
            partners = self.env['res.partner'].search([])
            partners.write({'lang': 'es_ES'})

    def _activate_multi_warehouse_and_location(self):
        """Activa el modo multialmacén y multiubicación en Odoo"""
        config = self.env['res.config.settings'].create({
            'group_stock_multi_warehouses': True,
            'group_stock_multi_locations': True,
        })
        config.execute()

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
