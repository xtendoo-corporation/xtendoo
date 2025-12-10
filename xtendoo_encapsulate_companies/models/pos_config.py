# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _default_picking_type_id(self):
        """
        Sobrescribimos para asegurar que al crear una caja POS se seleccione
        el tipo de operación (picking type) del almacén de la compañía actual.

        El método original puede fallar en entornos multi-compañía si el almacén
        de la compañía actual no tiene pos_type_id asignado.
        """
        company = self.env.company

        # Buscar almacén de la compañía actual
        warehouse = self.env['stock.warehouse'].with_context(active_test=False).search([
            ('company_id', '=', company.id)
        ], limit=1)

        if warehouse and warehouse.pos_type_id:
            _logger.info(
                f"POS Config: Usando pos_type_id={warehouse.pos_type_id.id} "
                f"del almacén '{warehouse.name}' (company_id={company.id})"
            )
            return warehouse.pos_type_id.id

        # Si no tiene pos_type_id, buscar un picking type de salida para esa compañía
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
            ('warehouse_id.company_id', '=', company.id)
        ], limit=1)

        if picking_type:
            _logger.info(
                f"POS Config: Usando picking_type alternativo={picking_type.id} "
                f"'{picking_type.name}' para company_id={company.id}"
            )
            return picking_type.id

        _logger.warning(
            f"POS Config: No se encontró picking type para company_id={company.id}. "
            f"Es posible que necesite crear los tipos de operación manualmente."
        )
        return False

    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribimos create para asegurar que el picking_type_id
        corresponda a la compañía del POS que se está creando.
        """
        for vals in vals_list:
            company_id = vals.get('company_id', self.env.company.id)
            company = self.env['res.company'].browse(company_id)

            # Si no se especificó picking_type_id o si el actual no corresponde a la compañía
            if not vals.get('picking_type_id'):
                # Buscar almacén de la compañía
                warehouse = self.env['stock.warehouse'].with_context(active_test=False).search([
                    ('company_id', '=', company_id)
                ], limit=1)

                if warehouse and warehouse.pos_type_id:
                    vals['picking_type_id'] = warehouse.pos_type_id.id
                    _logger.info(
                        f"POS Config create: Asignando pos_type_id={warehouse.pos_type_id.id} "
                        f"del almacén '{warehouse.name}' para company_id={company_id}"
                    )
                else:
                    # Buscar picking type de salida para esa compañía
                    picking_type = self.env['stock.picking.type'].search([
                        ('code', '=', 'outgoing'),
                        ('warehouse_id.company_id', '=', company_id)
                    ], limit=1)

                    if picking_type:
                        vals['picking_type_id'] = picking_type.id
                        _logger.info(
                            f"POS Config create: Asignando picking_type alternativo={picking_type.id} "
                            f"'{picking_type.name}' para company_id={company_id}"
                        )
                    else:
                        _logger.warning(
                            f"POS Config create: No se encontró picking type para company_id={company_id}"
                        )
            else:
                # Verificar que el picking_type_id especificado corresponde a la compañía
                picking_type = self.env['stock.picking.type'].browse(vals['picking_type_id'])
                if picking_type.warehouse_id.company_id.id != company_id:
                    _logger.warning(
                        f"POS Config create: El picking_type_id={vals['picking_type_id']} "
                        f"pertenece a otra compañía ({picking_type.warehouse_id.company_id.id}), "
                        f"buscando uno adecuado para company_id={company_id}"
                    )
                    # Buscar uno adecuado
                    warehouse = self.env['stock.warehouse'].with_context(active_test=False).search([
                        ('company_id', '=', company_id)
                    ], limit=1)

                    if warehouse and warehouse.pos_type_id:
                        vals['picking_type_id'] = warehouse.pos_type_id.id
                    else:
                        picking_type_new = self.env['stock.picking.type'].search([
                            ('code', '=', 'outgoing'),
                            ('warehouse_id.company_id', '=', company_id)
                        ], limit=1)
                        if picking_type_new:
                            vals['picking_type_id'] = picking_type_new.id

        return super().create(vals_list)

    @api.onchange('company_id')
    def _onchange_company_id_picking_type(self):
        """
        Cuando cambia la compañía, actualizar el picking_type_id
        para que corresponda con la nueva compañía.
        """
        if self.company_id:
            warehouse = self.env['stock.warehouse'].with_context(active_test=False).search([
                ('company_id', '=', self.company_id.id)
            ], limit=1)

            if warehouse and warehouse.pos_type_id:
                self.picking_type_id = warehouse.pos_type_id
            else:
                picking_type = self.env['stock.picking.type'].search([
                    ('code', '=', 'outgoing'),
                    ('warehouse_id.company_id', '=', self.company_id.id)
                ], limit=1)
                if picking_type:
                    self.picking_type_id = picking_type
                else:
                    self.picking_type_id = False

