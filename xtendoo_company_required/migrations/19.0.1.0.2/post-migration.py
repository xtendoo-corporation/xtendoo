from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Script de migración para corregir inconsistencias en las ubicaciones de stock
    de los partners con empresa asignada.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    _logger.info("Iniciando corrección de ubicaciones de stock para partners con empresa...")

    # Buscar todos los partners que tienen empresa asignada
    partners = env['res.partner'].search([('company_id', '!=', False)])

    fixed_count = 0
    error_count = 0

    for partner in partners:
        try:
            company = partner.company_id

            # Verificar si hay inconsistencias
            needs_fix = False

            if partner.property_stock_customer and \
               partner.property_stock_customer.company_id and \
               partner.property_stock_customer.company_id != company:
                needs_fix = True
                _logger.warning(
                    f"Partner '{partner.name}' (ID: {partner.id}): "
                    f"Ubicación de cliente inconsistente con la empresa"
                )

            if partner.property_stock_supplier and \
               partner.property_stock_supplier.company_id and \
               partner.property_stock_supplier.company_id != company:
                needs_fix = True
                _logger.warning(
                    f"Partner '{partner.name}' (ID: {partner.id}): "
                    f"Ubicación de proveedor inconsistente con la empresa"
                )

            if needs_fix:
                # Buscar ubicaciones correctas para la empresa del partner
                customer_location = env['stock.location'].search([
                    ('usage', '=', 'customer'),
                    ('company_id', '=', company.id)
                ], limit=1)

                if not customer_location:
                    customer_location = env['stock.location'].search([
                        ('usage', '=', 'customer'),
                        ('company_id', '=', False)
                    ], limit=1)

                supplier_location = env['stock.location'].search([
                    ('usage', '=', 'supplier'),
                    ('company_id', '=', company.id)
                ], limit=1)

                if not supplier_location:
                    supplier_location = env['stock.location'].search([
                        ('usage', '=', 'supplier'),
                        ('company_id', '=', False)
                    ], limit=1)

                # Actualizar las ubicaciones
                vals = {}
                if customer_location:
                    vals['property_stock_customer'] = customer_location.id
                if supplier_location:
                    vals['property_stock_supplier'] = supplier_location.id

                if vals:
                    # Usar SQL directo para evitar restricciones durante la migración
                    cr.execute("""
                        UPDATE ir_property
                        SET value_reference = %s
                        WHERE res_id = %s
                        AND name = 'property_stock_customer'
                        AND company_id = %s
                    """, (
                        f'stock.location,{customer_location.id}' if customer_location else None,
                        f'res.partner,{partner.id}',
                        company.id
                    ))

                    cr.execute("""
                        UPDATE ir_property
                        SET value_reference = %s
                        WHERE res_id = %s
                        AND name = 'property_stock_supplier'
                        AND company_id = %s
                    """, (
                        f'stock.location,{supplier_location.id}' if supplier_location else None,
                        f'res.partner,{partner.id}',
                        company.id
                    ))

                    fixed_count += 1
                    _logger.info(f"✓ Corregido partner '{partner.name}' (ID: {partner.id})")

        except Exception as e:
            error_count += 1
            _logger.error(
                f"✗ Error al corregir partner '{partner.name}' (ID: {partner.id}): {str(e)}"
            )

    _logger.info(
        f"Migración completada: {fixed_count} partners corregidos, {error_count} errores"
    )

