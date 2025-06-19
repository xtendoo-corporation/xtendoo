# -*- coding: utf-8 -*-
from odoo import models, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def set_spanish_language_for_all(self):
        """Establece el idioma español para todos los usuarios"""
        spanish_lang = self.env['res.lang'].search([('code', '=', 'es_ES')])
        if spanish_lang:
            # Cambiar el idioma para todos los usuarios
            users = self.search([])
            users.write({'lang': 'es_ES'})

            # Cambiar el idioma para todos los partners/contactos
            partners = self.env['res.partner'].search([])
            partners.write({'lang': 'es_ES'})

    @api.model
    def activate_multi_warehouse_and_location(self):
        """Activa el modo multialmacén y multiubicación en Odoo"""
        config = self.env['res.config.settings'].create({
            'group_stock_multi_warehouses': True,
            'group_stock_multi_locations': True,
        })
        config.execute()

    @api.model
    def translate_default_stock_locations(self):
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
        route.write({'name': 'Reabastecer bajo pedido (MTO)'})

    @api.model
    def update_sale_order_sequence(self):
        """Actualiza la secuencia de pedidos de venta para usar el prefijo VTA, incluir el año y reiniciar por año"""
        seq = self.env['ir.sequence'].search([('code', '=', 'sale.order')], limit=1)
        if seq:
            seq.write({
                'prefix': 'VTA/%(year)s/',
                'use_date_range': True,
            })

    @api.model
    def update_purchase_order_sequence(self):
        """Actualiza la secuencia de pedidos de compra para usar el prefijo COM, incluir el año y reiniciar por año"""
        seq = self.env['ir.sequence'].search([('code', '=', 'purchase.order')], limit=1)
        if seq:
            seq.write({
                'prefix': 'COM/%(year)s/',
                'use_date_range': True,
            })

    @api.model
    def update_invoice_sequence(self):
        """Actualiza la secuencia de facturas para usar el prefijo FAC, incluir el año y reiniciar por año"""
        seq = self.env['ir.sequence'].search([('code', '=', 'account.move')], limit=1)
        if seq:
            seq.write({
                'prefix': 'FAC/%(year)s/',
                'use_date_range': True,
            })
