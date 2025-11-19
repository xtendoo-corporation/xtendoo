# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# ===== Extensiones PostgreSQL necesarias =====
EXTENSIONS = ("pg_trgm", "unaccent")

# ===== Índices SQL =====
# Índices básicos que funcionan sin problemas con campos estándar
IDX_SQL_BASIC = [
    """CREATE INDEX IF NOT EXISTS idx_pt_pos_flags
       ON product_template (available_in_pos, active, company_id)""",
    """CREATE INDEX IF NOT EXISTS idx_pp_default_code
       ON product_product (default_code)""",
    """CREATE INDEX IF NOT EXISTS idx_pp_barcode
       ON product_product (barcode)""",
]

# Índices para búsquedas de texto en español (requieren extensiones)
# Nota: Solo creamos índice trigram en product_template ya que:
# - product_product no tiene columna 'name' directa (viene de template)
# - unaccent(lower()) no es IMMUTABLE y causa errores al crear índice
IDX_SQL_TEXT_ES = [
    """CREATE INDEX IF NOT EXISTS idx_pt_name_es_trgm
       ON product_template USING gin ((name->>'es_ES') gin_trgm_ops)""",
]

# ===== Configuración de Autovacuum por tabla =====
AUTOVAC_SETTINGS = {
    "product_template": {
        "autovacuum_vacuum_scale_factor": "0.05",
        "autovacuum_analyze_scale_factor": "0.02",
        "autovacuum_vacuum_threshold": "500",
        "autovacuum_analyze_threshold": "250",
    },
    "product_product": {
        "autovacuum_vacuum_scale_factor": "0.05",
        "autovacuum_analyze_scale_factor": "0.02",
        "autovacuum_vacuum_threshold": "500",
        "autovacuum_analyze_threshold": "250",
    },
    "pos_category": {
        "autovacuum_vacuum_scale_factor": "0.10",
        "autovacuum_analyze_scale_factor": "0.05",
    },
}

# ===== Índices para desinstalar =====
DROP_INDEXES = [
    "DROP INDEX IF EXISTS idx_pt_pos_flags",
    "DROP INDEX IF EXISTS idx_pp_default_code",
    "DROP INDEX IF EXISTS idx_pp_barcode",
    "DROP INDEX IF EXISTS idx_pt_name_es_trgm",
]


# ===== Funciones auxiliares =====

def _table_exists(cr, table: str) -> bool:
    """Verifica si una tabla existe en la base de datos."""
    cr.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema='public' AND table_name=%s
        """,
        (table,),
    )
    return bool(cr.fetchone())


def _create_extensions(cr):
    """Crea las extensiones PostgreSQL necesarias."""
    for ext in EXTENSIONS:
        try:
            cr.execute(f"CREATE EXTENSION IF NOT EXISTS {ext}")
            _logger.info("✓ Extensión PostgreSQL '%s' verificada/creada.", ext)
        except Exception as e:
            _logger.warning("⚠ No se pudo crear la extensión '%s': %s", ext, e)


def _create_indexes(cr):
    """Crea todos los índices necesarios para optimizar el POS."""
    statements = IDX_SQL_BASIC + IDX_SQL_TEXT_ES

    for sql in statements:
        savepoint_name = f"sp_{abs(hash(sql)) % 1000000}"
        try:
            cr.execute(f"SAVEPOINT {savepoint_name}")
            cr.execute(sql)
            idx_name = sql.split("idx_")[1].split()[0] if "idx_" in sql else "desconocido"
            _logger.info("✓ Índice creado: idx_%s", idx_name)
        except Exception as e:
            cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            # Si el índice ya existe, no es un error crítico
            if "already exists" in str(e):
                idx_name = sql.split("idx_")[1].split()[0] if "idx_" in sql else "desconocido"
                _logger.info("  Índice idx_%s ya existe (omitido).", idx_name)
            else:
                _logger.warning("⚠ Fallo creando índice: %s", e)
        finally:
            try:
                cr.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            except:
                pass  # Savepoint ya fue liberado


def _apply_autovacuum_settings(cr):
    """Aplica configuración personalizada de autovacuum a las tablas críticas."""
    for table, params in AUTOVAC_SETTINGS.items():
        if not _table_exists(cr, table):
            _logger.info("  Tabla '%s' no existe; omitiendo autovacuum.", table)
            continue

        savepoint_name = f"sp_autovac_{abs(hash(table)) % 1000000}"
        try:
            cr.execute(f"SAVEPOINT {savepoint_name}")
            pairs = ", ".join(f"{k} = {v}" for k, v in params.items())
            sql = f"ALTER TABLE {table} SET ({pairs})"
            cr.execute(sql)
            _logger.info("✓ Autovacuum configurado en '%s'.", table)
        except Exception as e:
            cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            _logger.warning("⚠ No se pudo configurar autovacuum en '%s': %s", table, e)
        finally:
            try:
                cr.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            except:
                pass


def _reset_autovacuum_settings(cr):
    """Resetea la configuración de autovacuum a valores por defecto."""
    keys = set()
    for p in AUTOVAC_SETTINGS.values():
        keys.update(p.keys())
    keys_csv = ", ".join(keys)

    for table in AUTOVAC_SETTINGS.keys():
        if not _table_exists(cr, table):
            continue
        try:
            sql = f"ALTER TABLE {table} RESET ({keys_csv})"
            cr.execute(sql)
            _logger.info("✓ Autovacuum reseteado en '%s'.", table)
        except Exception as e:
            _logger.warning("⚠ No se pudo resetear autovacuum en '%s': %s", table, e)


def _analyze_tables(cr):
    """Ejecuta ANALYZE en las tablas críticas para actualizar estadísticas."""
    for table in ("product_template", "product_product", "pos_category"):
        if _table_exists(cr, table):
            try:
                cr.execute(f"ANALYZE {table}")
                _logger.info("✓ ANALYZE ejecutado en '%s'.", table)
            except Exception as e:
                _logger.warning("⚠ Fallo en ANALYZE de '%s': %s", table, e)


def _drop_indexes(cr):
    """Elimina todos los índices creados por el módulo."""
    for sql in DROP_INDEXES:
        try:
            cr.execute(sql)
            idx_name = sql.split("idx_")[1].split()[0] if "idx_" in sql else "desconocido"
            _logger.info("✓ Índice eliminado: idx_%s", idx_name)
        except Exception as e:
            _logger.warning("⚠ Fallo eliminando índice: %s", e)


def _set_default_parameters(env):
    """Establece los parámetros de configuración por defecto si no existen."""
    IrConfigParameter = env['ir.config_parameter']

    params = {
        'point_of_sale.limited_product_count': '500',
        'point_of_sale.limited_customer_count': '500',
    }

    for key, value in params.items():
        existing = IrConfigParameter.search([('key', '=', key)], limit=1)
        if not existing:
            IrConfigParameter.create({'key': key, 'value': value})
            _logger.info("✓ Parámetro creado: %s = %s", key, value)
        else:
            _logger.info("  Parámetro %s ya existe con valor: %s", key, existing.value)


# ===== Hooks del módulo =====

def post_init_hook(env):
    """
    Se ejecuta tras instalar el módulo.

    Crea:
    - Parámetros de configuración por defecto (si no existen)
    - Extensiones PostgreSQL (pg_trgm, unaccent)
    - Índices optimizados en tablas de productos
    - Configuración personalizada de autovacuum
    - Actualiza estadísticas de las tablas
    """
    cr = env.cr
    _logger.info("=" * 70)
    _logger.info("XTENDOO POS PERFORMANCE: Iniciando optimizaciones...")
    _logger.info("=" * 70)

    _set_default_parameters(env)
    _create_extensions(cr)
    _create_indexes(cr)
    _apply_autovacuum_settings(cr)
    _analyze_tables(cr)

    _logger.info("=" * 70)
    _logger.info("XTENDOO POS PERFORMANCE: Optimizaciones completadas.")
    _logger.info("=" * 70)
    _logger.info("")
    _logger.info("SIGUIENTE PASO:")
    _logger.info("  → Vaya a Ajustes → Punto de venta")
    _logger.info("  → Ajuste los límites de productos/clientes según su catálogo")
    _logger.info("  → Valores actuales: 500 productos, 500 clientes")
    _logger.info("")


def uninstall_hook(env):
    """
    Se ejecuta al desinstalar el módulo.

    Elimina:
    - Todos los índices creados
    - Configuración personalizada de autovacuum

    Nota: Los parámetros del sistema y las extensiones PostgreSQL
    se mantienen ya que pueden ser utilizados por otros módulos.
    """
    cr = env.cr
    _logger.info("=" * 70)
    _logger.info("XTENDOO POS PERFORMANCE: Limpiando optimizaciones...")
    _logger.info("=" * 70)

    _drop_indexes(cr)
    _reset_autovacuum_settings(cr)

    _logger.info("=" * 70)
    _logger.info("XTENDOO POS PERFORMANCE: Limpieza completada.")
    _logger.info("=" * 70)
    _logger.info("")
    _logger.info("NOTA:")
    _logger.info("  • Los índices han sido eliminados")
    _logger.info("  • Los parámetros de sistema se mantienen para referencia")
    _logger.info("  • Las extensiones PostgreSQL se mantienen (pueden ser usadas por otros módulos)")
    _logger.info("")

