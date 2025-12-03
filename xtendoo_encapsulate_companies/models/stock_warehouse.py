# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribimos el create para:
        1. Crear las ubicaciones mínimas necesarias (view y stock) con la compañía correcta
        2. Crear el almacén básico SIN crear automáticamente tipos de operación, rutas, etc.

        Esto evita los problemas de inconsistencia de compañías entre registros relacionados.
        El usuario puede crear manualmente los tipos de operación y rutas después si los necesita.
        """
        for vals in vals_list:
            company_id = vals.get('company_id')

            if not company_id:
                company_id = self.env.company.id
                vals['company_id'] = company_id

            # Asegurar datos mínimos del almacén
            if not vals.get('name'):
                company = self.env['res.company'].browse(company_id)
                vals['name'] = company.name

            if not vals.get('code'):
                company = self.env['res.company'].browse(company_id)
                vals['code'] = company.name[:5]

            if not vals.get('partner_id'):
                company = self.env['res.company'].browse(company_id)
                vals['partner_id'] = company.partner_id.id

            _logger.info(
                f"Creando almacén '{vals.get('name')}' (código: {vals.get('code')}) "
                f"para company_id={company_id}"
            )

            # Crear ubicación view (obligatoria) - debe tener la misma compañía que el almacén
            if not vals.get('view_location_id'):
                view_loc = self.env['stock.location'].create({
                    'name': vals.get('code'),
                    'usage': 'view',
                    'company_id': company_id,  # Misma compañía que el almacén
                })
                vals['view_location_id'] = view_loc.id
                _logger.info(f"Ubicación view creada: {view_loc.name} (id={view_loc.id}) con company_id={company_id}")

            # Crear ubicación stock (obligatoria) - esta SÍ tiene compañía
            if not vals.get('lot_stock_id'):
                stock_loc = self.env['stock.location'].create({
                    'name': 'Stock',
                    'usage': 'internal',
                    'location_id': vals['view_location_id'],
                    'company_id': company_id,
                })
                vals['lot_stock_id'] = stock_loc.id
                _logger.info(f"Ubicación stock creada: {stock_loc.name} (id={stock_loc.id})")

        # Llamar directamente al create de models.Model para saltarnos toda la lógica
        # del stock.warehouse.create que crea picking types, rutas, reglas, etc.
        warehouses = models.Model.create(self, vals_list)

        # Actualizar el warehouse_id en las ubicaciones creadas
        for warehouse in warehouses:
            warehouse.view_location_id.with_context(active_test=False).search([
                ('id', 'child_of', warehouse.view_location_id.id)
            ]).write({'warehouse_id': warehouse.id})

        _logger.info(
            f"Almacén(es) creado(s) exitosamente sin tipos de operación ni rutas automáticas. "
            f"IDs: {warehouses.ids}"
        )

        return warehouses
