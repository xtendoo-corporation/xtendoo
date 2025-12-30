# MIS Report Spanish Reports - Quick Access

## Descripción

Este módulo proporciona acceso directo a través del menú para crear y visualizar todos los informes MIS españoles principales (Balance y PyG).

## Características

- Añade **6 opciones de menú** bajo "Finanzas > MIS Reports" para diferentes tipos de informes:
  1. **Balance Abreviado** - Balance Abreviado (PGCE 2008)
  2. **Balance Normal** - Balance Normal (PGCE 2008)
  3. **PyG Abreviado** - Pérdidas y Ganancias Abreviado
  4. **PyG Normal** - Pérdidas y Ganancias Completo
  5. **Balance PYMES** - Balance para PYMES
  6. **PyG PYMES** - Pérdidas y Ganancias para PYMES

- **Creación automática**: Si no existe un informe para el año actual, lo crea automáticamente
- **Filtrado inteligente**: Cada menú muestra solo informes de su tipo específico
- **Vista de lista**: Permite gestionar múltiples informes (diferentes años, comparativas, etc.)
- **Integración completa** con el visor estándar de MIS Builder

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
├── models/
│   ├── __init__.py
│   └── mis_report_instance.py  (6 métodos + 1 método genérico)
├── static/
│   └── description/
│       └── index.html
└── views/
    └── menu_views.xml  (6 acciones + 6 menús)
```

## Informes Disponibles

### Balance Sheets (Balances)

| Menú | Template | Descripción |
|------|----------|-------------|
| Balance Abreviado | `mis_report_es_balance_abreviado` | Para empresas pequeñas |
| Balance Normal | `mis_report_es_balance_normal` | Formato estándar completo |
| Balance PYMES | `mis_report_es_balance_pymes` | Específico para PYMES |

### Profit & Loss (Pérdidas y Ganancias)

| Menú | Template | Descripción |
|------|----------|-------------|
| PyG Abreviado | `mis_report_es_pyg_abreviado` | Formato simplificado |
| PyG Normal | `mis_report_es_pyg_normal` | Formato completo detallado |
| PyG PYMES | `mis_report_es_pyg_pymes` | Específico para PYMES |

## Ventajas

- **Todo en un módulo**: Una sola instalación proporciona acceso a todos los informes españoles
- **Consistencia**: Todos los informes funcionan de la misma manera
- **Automatización**: Creación automática del informe del año actual
- **Flexibilidad**: Permite crear múltiples informes por tipo
- **Facilidad de uso**: Menús claros y organizados

## Autor

Xtendoo Corporation

## Licencia

LGPL-3.0 or later

