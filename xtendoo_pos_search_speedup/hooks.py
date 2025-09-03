# -*- coding: utf-8 -*-
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# ===== Extensiones necesarias =====
EXTENSIONS = ("pg_trgm", "unaccent")

# ===== SQL índices =====
# Índices básicos que funcionan sin problemas con campos estándar
IDX_SQL_BASIC = [
    """CREATE INDEX IF NOT EXISTS idx_pt_pos_flags
       ON product_template (available_in_pos, active, company_id)""",
    """CREATE INDEX IF NOT EXISTS idx_pp_default_code
       ON product_product (default_code)""",
    """CREATE INDEX IF NOT EXISTS idx_pp_barcode
       ON product_product (barcode)""",
]

# Índices para búsquedas de texto en español
IDX_SQL_TEXT_ES = [
    """CREATE INDEX IF NOT EXISTS idx_pt_name_es_trgm
       ON product_template USING gin ((name->>'es_ES') gin_trgm_ops)""",
    """CREATE INDEX IF NOT EXISTS idx_pt_name_es_unaccent
       ON product_template (unaccent(lower(name->>'es_ES')))""",
    """CREATE INDEX IF NOT EXISTS idx_pp_name_es_trgm
       ON product_product USING gin ((name->>'es_ES') gin_trgm_ops)""",
    """CREATE INDEX IF NOT EXISTS idx_pp_name_es_unaccent
       ON product_product (unaccent(lower(name->>'es_ES')))""",
]

# ===== Autovacuum por tabla =====
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

# ===== Parámetros POS para limitar carga inicial =====
POS_LIMIT_PARAMS = {
    "point_of_sale.limited_product_count": 10000,
    # Descomenta si también quieres limitar clientes en POS:
    "point_of_sale.limited_customer_count": 10000,
}

# Para desinstalación (índices)
DROP_INDEXES = [
    "DROP INDEX IF EXISTS idx_pt_pos_flags",
    "DROP INDEX IF EXISTS idx_pp_default_code",
    "DROP INDEX IF EXISTS idx_pp_barcode",
    "DROP INDEX IF EXISTS idx_pt_name_es_trgm",
    "DROP INDEX IF EXISTS idx_pt_name_es_unaccent",
    "DROP INDEX IF EXISTS idx_pp_name_es_trgm",
    "DROP INDEX IF EXISTS idx_pp_name_es_unaccent",
]

def _set_autocommit(cr, enabled: bool):
    cnx = getattr(cr, "_cnx", None)
    if cnx is None:
        _logger.warning("No se pudo acceder a la conexión; CONCURRENTLY puede fallar.")
        return
    cnx.autocommit = enabled

def _column_exists(cr, table: str, column: str) -> bool:
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return bool(cr.fetchone())

def _table_exists(cr, table: str) -> bool:
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
    for ext in EXTENSIONS:
        try:
            cr.execute(f"CREATE EXTENSION IF NOT EXISTS {ext}")
            _logger.info("Extensión %s verificada/creada.", ext)
        except Exception as e:
            _logger.warning("No se pudo crear la extensión %s: %s", ext, e)

def _create_indexes_concurrently(cr):
    statements = IDX_SQL_BASIC + IDX_SQL_TEXT_ES

    # Crear cada índice individualmente con manejo de errores usando savepoints
    for sql in statements:
        savepoint_name = f"sp_{hash(sql) % 1000000}"
        try:
            cr.execute(f"SAVEPOINT {savepoint_name}")
            cr.execute(sql)
            _logger.info("OK índice: %s", sql.split("ON", 1)[0].strip())
        except Exception as e:
            cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            # Si el índice ya existe, no es un error crítico
            if "already exists" in str(e):
                _logger.info("Índice ya existe: %s", sql.split("ON", 1)[0].strip())
            else:
                _logger.warning("Fallo creando índice (%s): %s", sql, e)
        finally:
            try:
                cr.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            except:
                pass  # Savepoint ya fue liberado

def _apply_autovacuum_settings(cr):
    for table, params in AUTOVAC_SETTINGS.items():
        savepoint_name = f"sp_autovac_{hash(table) % 1000000}"
        try:
            cr.execute(f"SAVEPOINT {savepoint_name}")
            if not _table_exists(cr, table):
                _logger.info("Tabla %s no existe; se omiten ajustes de autovacuum.", table)
                continue
            pairs = ", ".join(f"{k} = {v}" for k, v in params.items())
            sql = f"ALTER TABLE {table} SET ({pairs})"
            cr.execute(sql)
            _logger.info("Autovacuum ajustado en %s: %s", table, pairs)
        except Exception as e:
            cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            _logger.warning("No se pudo ajustar autovacuum en %s: %s", table, e)
        finally:
            try:
                cr.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            except:
                pass

def _reset_autovacuum_settings(cr):
    keys = set()
    for p in AUTOVAC_SETTINGS.values():
        keys.update(p.keys())
    keys_csv = ", ".join(keys)
    for table in AUTOVAC_SETTINGS.keys():
        if not _table_exists(cr, table):
            continue
        sql = f"ALTER TABLE {table} RESET ({keys_csv})"
        try:
            cr.execute(sql)
            _logger.info("Autovacuum reseteado en %s.", table)
        except Exception as e:
            _logger.warning("No se pudo resetear autovacuum en %s: %s", table, e)

def _analyze_tables(cr):
    for table in ("product_template", "product_product", "pos_category"):
        if _table_exists(cr, table):
            try:
                cr.execute(f"ANALYZE {table}")
                _logger.info("ANALYZE ejecutado en %s.", table)
            except Exception as e:
                _logger.warning("Fallo en ANALYZE %s: %s", table, e)

def _set_pos_limits(env):
    icp = env["ir.config_parameter"].sudo()
    for key, value in POS_LIMIT_PARAMS.items():
        try:
            icp.set_param(key, str(value))
            _logger.info("Parametro POS %s establecido a %s", key, value)
        except Exception as e:
            _logger.warning("No se pudo establecer %s: %s", key, e)

def _reset_pos_limits(env):
    icp = env["ir.config_parameter"].sudo()
    for key in POS_LIMIT_PARAMS.keys():
        try:
            recs = icp.search([("key", "=", key)])
            if recs:
                recs.unlink()
                _logger.info("Parametro POS %s eliminado.", key)
        except Exception as e:
            _logger.warning("No se pudo eliminar %s: %s", key, e)

def post_init_hook(env):
    """Se ejecuta tras instalar el módulo."""
    cr = env.cr
    registry = env.registry
    _logger.info("POS Speedup: creando extensiones, índices, autovacuum y límites de POS…")
    _create_extensions(cr)
    _create_indexes_concurrently(cr)
    _apply_autovacuum_settings(cr)
    _analyze_tables(cr)
    _set_pos_limits(env)
    _logger.info("POS Speedup: terminado.")

def uninstall_hook(env):
    """Si desinstalas, elimina los índices para dejar la BD limpia."""
    cr = env.cr
    registry = env.registry
    _logger.info("POS Speedup: eliminando índices, reseteando autovacuum y parámetros POS…")
    for sql in DROP_INDEXES:
        try:
            _set_autocommit(cr, True)
            cr.execute(sql)
            _logger.info("OK drop: %s", sql)
        except Exception as e:
            _logger.warning("Fallo eliminando índice (%s): %s", sql, e)
        finally:
            _set_autocommit(cr, False)
    _reset_autovacuum_settings(cr)
    _reset_pos_limits(env)
    _logger.info("POS Speedup: terminado.")
