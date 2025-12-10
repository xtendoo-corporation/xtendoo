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
        3. Crear los tipos de operación básicos (recepción, envío y POS) con la compañía correcta

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

        # Actualizar el warehouse_id en las ubicaciones creadas y crear tipos de operación básicos
        for warehouse in warehouses:
            warehouse.view_location_id.with_context(active_test=False).search([
                ('id', 'child_of', warehouse.view_location_id.id)
            ]).write({'warehouse_id': warehouse.id})

            # Crear tipos de operación básicos con la compañía correcta
            warehouse._create_basic_picking_types()

        _logger.info(
            f"Almacén(es) creado(s) exitosamente con tipos de operación básicos. "
            f"IDs: {warehouses.ids}"
        )

        return warehouses

    def _create_basic_picking_types(self):
        """
        Crea los tipos de operación básicos para el almacén:
        - Recepciones (incoming)
        - Entregas (outgoing)
        - Operaciones POS (outgoing específico para point_of_sale)

        Todos con la compañía correcta del almacén.

        NOTA: No asignamos ubicaciones de origen/destino por defecto para evitar
        problemas de inconsistencia de compañía con ubicaciones virtuales globales
        (Proveedores, Clientes) que no tienen company_id.
        """
        self.ensure_one()

        company_id = self.company_id.id
        stock_location = self.lot_stock_id

        picking_types_to_create = {}

        # Tipo de operación: Recepciones (IN)
        # No asignamos default_location_src_id porque la ubicación de proveedores
        # es global (sin compañía) y causa error de inconsistencia
        if not self.in_type_id:
            in_sequence = self.env['ir.sequence'].create({
                'name': f'{self.name} Secuencia IN',
                'prefix': f'{self.code}/IN/',
                'padding': 5,
                'company_id': company_id,
            })
            picking_types_to_create['in_type_id'] = {
                'name': f'{self.name}: Recepciones',
                'code': 'incoming',
                'sequence_id': in_sequence.id,
                'default_location_dest_id': stock_location.id,
                'warehouse_id': self.id,
                'company_id': company_id,
                'sequence_code': 'IN',
            }
            _logger.info(f"Preparando tipo de operación Recepciones para almacén {self.name} (company_id={company_id})")

        # Tipo de operación: Entregas (OUT)
        # No asignamos default_location_dest_id porque la ubicación de clientes
        # es global (sin compañía) y causa error de inconsistencia
        if not self.out_type_id:
            out_sequence = self.env['ir.sequence'].create({
                'name': f'{self.name} Secuencia OUT',
                'prefix': f'{self.code}/OUT/',
                'padding': 5,
                'company_id': company_id,
            })
            picking_types_to_create['out_type_id'] = {
                'name': f'{self.name}: Entregas',
                'code': 'outgoing',
                'sequence_id': out_sequence.id,
                'default_location_src_id': stock_location.id,
                'warehouse_id': self.id,
                'company_id': company_id,
                'sequence_code': 'OUT',
            }
            _logger.info(f"Preparando tipo de operación Entregas para almacén {self.name} (company_id={company_id})")

        # Tipo de operación: POS (solo si el módulo point_of_sale está instalado)
        # No asignamos default_location_dest_id porque la ubicación de clientes
        # es global (sin compañía) y causa error de inconsistencia
        if hasattr(self, 'pos_type_id') and not self.pos_type_id:
            pos_sequence = self.env['ir.sequence'].create({
                'name': f'{self.name} Secuencia POS',
                'prefix': f'{self.code}/POS/',
                'padding': 5,
                'company_id': company_id,
            })
            picking_types_to_create['pos_type_id'] = {
                'name': f'{self.name}: Pedidos POS',
                'code': 'outgoing',
                'sequence_id': pos_sequence.id,
                'default_location_src_id': stock_location.id,
                'warehouse_id': self.id,
                'company_id': company_id,
                'sequence_code': 'POS',
            }
            _logger.info(f"Preparando tipo de operación POS para almacén {self.name} (company_id={company_id})")

        # Tipo de operación: Interno (INT)
        if not self.int_type_id:
            int_sequence = self.env['ir.sequence'].create({
                'name': f'{self.name} Secuencia INT',
                'prefix': f'{self.code}/INT/',
                'padding': 5,
                'company_id': company_id,
            })
            picking_types_to_create['int_type_id'] = {
                'name': f'{self.name}: Transferencias Internas',
                'code': 'internal',
                'sequence_id': int_sequence.id,
                'default_location_src_id': stock_location.id,
                'default_location_dest_id': stock_location.id,
                'warehouse_id': self.id,
                'company_id': company_id,
                'sequence_code': 'INT',
            }
            _logger.info(f"Preparando tipo de operación Transferencias Internas para almacén {self.name} (company_id={company_id})")

        # Crear todos los tipos de operación y asignarlos al almacén
        update_vals = {}
        for field_name, picking_type_vals in picking_types_to_create.items():
            picking_type = self.env['stock.picking.type'].create(picking_type_vals)
            update_vals[field_name] = picking_type.id
            _logger.info(f"Tipo de operación '{picking_type.name}' creado (id={picking_type.id}, company_id={company_id})")

        if update_vals:
            # Usar SQL directo para evitar triggers
            self.write(update_vals)

