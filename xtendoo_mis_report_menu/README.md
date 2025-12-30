# MIS Report Spanish Reports - Quick Access

## Descripción

Este módulo proporciona acceso directo a través del menú para crear y visualizar todos los informes MIS españoles principales (Balance y PyG), con estilos personalizados mejorados.

## Características

- Añade **9 opciones de menú** bajo "Finanzas > MIS Reports" para diferentes tipos de informes:
  1. **Balance Abreviado** - Balance abreviado (PGCE 2008)
  2. **Balance Completo** - Balance completo (PGCE 2008)
  3. **Balance PYMES** - Balance PYMEs (PGCE 2008)
  4. **Balance PYMESFL** - Balance de pequeñas y medianas entidades sin fines lucrativos
  5. **PyG Abreviado** - Pérdidas y ganancias abreviado (PGCE 2008)
  6. **PyG Completo** - Pérdidas y ganancias completo (PGCE 2008)
  7. **PyG PYMES** - Pérdidas y ganancias PYMEs (PGCE 2008)
  8. **PyG PYMESFL** - Pérdidas y ganancias de pequeñas y medianas entidades sin fines lucrativos
  9. **Estado de Ingresos y Gastos Reconocidos** - Estado de ingresos y gastos reconocidos (PGCE 2008)

- **Creación automática**: Si no existe un informe para el año actual, lo crea automáticamente
- **Filtrado inteligente**: Cada menú muestra solo informes de su tipo específico
- **Vista de lista**: Permite gestionar múltiples informes (diferentes años, comparativas, etc.)
- **Integración completa** con el visor estándar de MIS Builder
- **Estilos personalizados**: Mejora la legibilidad de los informes con:
  - Color de fondo gris (#d3d3d3) en lugar de naranja para títulos principales
  - Sin formato itálico en todos los estilos (mejor legibilidad)

## Dependencias

- mis_builder
- l10n_es_mis_report

## Instalación

1. Asegúrese de que los módulos `mis_builder` y `l10n_es_mis_report` estén instalados
2. Actualice la lista de módulos
3. Instale el módulo `xtendoo_mis_report_menu`

## Uso

1. Vaya a **Finanzas > MIS Reports**
2. Verá 6 nuevas opciones de menú (una por cada tipo de informe)
3. Al hacer clic en cualquiera:
   - Se crea automáticamente un informe para el año actual si no existe
   - Se muestra una lista con todos los informes de ese tipo
   - Puede crear, editar, eliminar o ejecutar informes desde la lista

## Estructura del módulo

```
xtendoo_mis_report_menu/
├── __init__.py
├── __manifest__.py
├── README.md
├── DOCUMENTATION.md
├── data/
│   └── mis_report_styles.xml  (Estilos personalizados)
├── models/
│   ├── __init__.py
│   └── mis_report_instance.py  (9 métodos + 1 método genérico)
├── static/
│   └── description/
│       └── index.html
└── views/
    └── menu_views.xml  (9 acciones + 9 menús)
```

## Informes Disponibles

### Balance Sheets (Balances)

| Menú | Template | Descripción |
|------|----------|-------------|
| Balance Abreviado | `mis_report_es_balance_abreviado` | Balance abreviado (PGCE 2008) |
| Balance Completo | `mis_report_es_balance_normal` | Balance completo (PGCE 2008) |
| Balance PYMES | `mis_report_es_balance_pymes` | Balance PYMEs (PGCE 2008) |
| Balance PYMESFL | `mis_report_es_balance_pymes_sfl` | Balance de pequeñas y medianas entidades sin fines lucrativos |

### Profit & Loss (Pérdidas y Ganancias)

| Menú | Template | Descripción |
|------|----------|-------------|
| PyG Abreviado | `mis_report_es_pyg_abreviado` | Pérdidas y ganancias abreviado (PGCE 2008) |
| PyG Completo | `mis_report_es_pyg_normal` | Pérdidas y ganancias completo (PGCE 2008) |
| PyG PYMES | `mis_report_es_pyg_pymes` | Pérdidas y ganancias PYMEs (PGCE 2008) |
| PyG PYMESFL | `mis_report_es_pyg_pyme_sfl` | Pérdidas y ganancias de pequeñas y medianas entidades sin fines lucrativos |

### Otros Informes

| Menú | Template | Descripción |
|------|----------|-------------|
| Estado de Ingresos y Gastos Reconocidos | `mis_report_es_eiyg_normal` | Estado de ingresos y gastos reconocidos (PGCE 2008) |

## Ventajas

- **Todo en un módulo**: Una sola instalación proporciona acceso a todos los informes españoles
- **Consistencia**: Todos los informes funcionan de la misma manera
- **Automatización**: Creación automática del informe del año actual
- **Flexibilidad**: Permite crear múltiples informes por tipo
- **Facilidad de uso**: Menús claros y organizados
- **Mejor legibilidad**: Estilos mejorados sin itálicas y con colores más neutros

## Estilos Personalizados

Este módulo sobrescribe los estilos predeterminados de `l10n_es_mis_report` para mejorar la legibilidad:

### Cambios Aplicados:

| Estilo | Cambio Original → Nuevo |
|--------|------------------------|
| **l1** | Fondo naranja (#ffa500) → Gris (#d3d3d3) |
| **l1i** | Fondo naranja + Itálica → Gris sin itálica |
| **l2i** | Negrita + Itálica → Negrita sin itálica |
| **l3i** | Nivel 1 + Itálica → Nivel 1 sin itálica |
| **l4i** | Nivel 2 + Itálica → Nivel 2 sin itálica |
| **l5i** | Nivel 3 + Itálica → Nivel 3 sin itálica |
| **l6i** | Nivel 4 + Itálica → Nivel 4 sin itálica |

### Ventajas de los Nuevos Estilos:

- ✅ **Mayor legibilidad**: El gris es menos agresivo visualmente que el naranja
- ✅ **Sin itálicas**: Mejora la lectura en pantalla y al imprimir
- ✅ **Más profesional**: Colores neutros más adecuados para informes financieros
- ✅ **Mejor contraste**: El gris mantiene buen contraste con el texto negro

## Autor

Xtendoo Corporation

## Licencia

LGPL-3.0 or later

