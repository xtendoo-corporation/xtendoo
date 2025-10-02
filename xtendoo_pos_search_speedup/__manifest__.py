# -*- coding: utf-8 -*-
{
    "name": "Xtendoo POS Search Speedup (Indexes)",
    "version": "19.0.1.0.0",
    "summary": "Acelera carga y búsquedas del POS creando extensiones/índices en PostgreSQL",
    "description": """
Módulo de Optimización del Rendimiento del POS
===============================================

Este módulo optimiza significativamente el rendimiento del Punto de Venta mediante:

**Extensiones PostgreSQL:**
* pg_trgm: Para búsquedas aproximadas de texto
* unaccent: Para búsquedas sin acentos

**Índices Optimizados:**
* Campos de productos (código de barras, referencia)
* Filtros del POS (disponible en POS, activo, compañía)

**Configuración de Autovacuum:**
* Mantenimiento automático optimizado de tablas de productos
* Umbrales ajustados para mejor rendimiento

**Límites de Carga:**
* Máximo 10,000 productos en POS
* Máximo 10,000 clientes en POS

**Beneficios:**
* Búsquedas más rápidas por código de barras
* Carga inicial del POS acelerada
* Mejor rendimiento general en operaciones del POS
    """,
    "category": "Point of Sale",
    "license": "LGPL-3",
    "author": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "depends": ["point_of_sale", "product"],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "auto_install": False,
}
