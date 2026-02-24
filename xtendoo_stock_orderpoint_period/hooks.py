# -*- coding: utf-8 -*-
# Copyright 2026 Xtendoo Corporation
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import logging

_logger = logging.getLogger(__name__)


def pre_init_hook(env):
    """Elimina el constraint UNIQUE (product_id, location_id, company_id)
    de stock.warehouse.orderpoint para permitir múltiples orderpoints
    con diferentes períodos (date_start/date_end) para el mismo
    producto/ubicación.

    Odoo 19 define este constraint como:
        _product_location_check = models.Constraint(
            'unique (product_id, location_id, company_id)',
            'A replenishment rule already exists for this product on this location.',
        )

    El nombre en PostgreSQL sigue la convención:
        stock_warehouse_orderpoint__product_location_check

    VERIFY IN SOURCE – Si la convención de nombres cambia, buscar en la
    tabla pg_constraint:
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'stock_warehouse_orderpoint'::regclass
        AND contype = 'u';
    """
    cr = env.cr
    # Intentar con el nombre convencional de Odoo 19 (models.Constraint)
    constraint_names = [
        "stock_warehouse_orderpoint__product_location_check",
        # Alternativa: nombre generado por formato antiguo
        "stock_warehouse_orderpoint_product_location_check",
    ]

    for constraint_name in constraint_names:
        cr.execute(
            """
            SELECT 1 FROM pg_constraint
            WHERE conname = %s
            AND conrelid = 'stock_warehouse_orderpoint'::regclass
            """,
            (constraint_name,),
        )
        if cr.fetchone():
            _logger.info(
                "Eliminando constraint '%s' de stock_warehouse_orderpoint "
                "para permitir múltiples orderpoints por período.",
                constraint_name,
            )
            cr.execute(
                "ALTER TABLE stock_warehouse_orderpoint DROP CONSTRAINT %s"
                % constraint_name  # Seguro: nombre controlado, no input externo
            )
            _logger.info("Constraint '%s' eliminado correctamente.", constraint_name)
            return

    _logger.warning(
        "No se encontró el constraint unique (product_id, location_id, company_id) "
        "en stock_warehouse_orderpoint. Puede que ya haya sido eliminado o que "
        "el nombre sea diferente. Ejecuta:\n"
        "  SELECT conname FROM pg_constraint\n"
        "  WHERE conrelid = 'stock_warehouse_orderpoint'::regclass AND contype = 'u';\n"
        "para verificar."
    )
