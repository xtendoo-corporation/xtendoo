# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.depends('code')
    def _compute_default_location_src_id(self):
        """
        Sobrescribimos para evitar usar la ubicación global de Proveedores
        que no tiene company_id y causa errores de inconsistencia en multi-compañía.

        En su lugar, usamos la ubicación de stock del almacén para todos los casos.
        """
        for picking_type in self:
            if picking_type.warehouse_id and picking_type.warehouse_id.lot_stock_id:
                picking_type.default_location_src_id = picking_type.warehouse_id.lot_stock_id.id
            elif picking_type.company_id:
                warehouse = self.env['stock.warehouse'].search([
                    ('company_id', '=', picking_type.company_id.id)
                ], limit=1)
                if warehouse and warehouse.lot_stock_id:
                    picking_type.default_location_src_id = warehouse.lot_stock_id.id
                else:
                    picking_type.default_location_src_id = False
            else:
                picking_type.default_location_src_id = False

    @api.depends('code')
    def _compute_default_location_dest_id(self):
        """
        Sobrescribimos para evitar usar la ubicación global de Clientes
        que no tiene company_id y causa errores de inconsistencia en multi-compañía.

        En su lugar, usamos la ubicación de stock del almacén para todos los casos.
        """
        for picking_type in self:
            if picking_type.warehouse_id and picking_type.warehouse_id.lot_stock_id:
                picking_type.default_location_dest_id = picking_type.warehouse_id.lot_stock_id.id
            elif picking_type.company_id:
                warehouse = self.env['stock.warehouse'].search([
                    ('company_id', '=', picking_type.company_id.id)
                ], limit=1)
                if warehouse and warehouse.lot_stock_id:
                    picking_type.default_location_dest_id = warehouse.lot_stock_id.id
                else:
                    picking_type.default_location_dest_id = False
            else:
                picking_type.default_location_dest_id = False

