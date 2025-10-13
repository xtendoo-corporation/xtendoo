# Account Bank Statement Line - Full Edit

## Descripción

Este módulo permite editar todos los campos del modelo de líneas de extracto bancario (`account.bank.statement.line`) en Odoo 17, proporcionando acceso directo a través de un menú dedicado.

## Objetivo

- Habilitar la edición completa de líneas de extracto bancario
- Proporcionar acceso directo mediante menú propio
- Permitir correcciones de descuadres con control de permisos
- Mantener trazabilidad completa de todos los cambios

## Características

### 1. Edición Total de Campos
- Permite modificar todos los campos de `account.bank.statement.line`
- Elimina restricciones de solo lectura en vistas
- Habilitación de campos compute con inverse cuando sea posible

### 2. Seguridad y Permisos
- **Grupo específico**: "Xtendoo - Editor líneas de extracto" (`group_xtendoo_bank_line_editor`)
- Solo usuarios en `account.group_account_manager` o en el grupo específico pueden editar
- Control granular mediante `ir.model.access`

### 3. Trazabilidad y Auditoría
- Registro completo en chatter (mail.thread) de todos los cambios
- Campo `manual_adjustment_reason` para documentar el motivo del ajuste
- Tracking automático en campos clave

### 4. Control de Riesgos
- Parámetro de configuración: `account_banck_statement_line.allow_full_edit`
- Wizard de confirmación para ediciones en estados críticos (posted/reconciled)
- Banner de advertencia en formulario cuando el extracto está conciliado o posteado
- Botón para recalcular totales y conciliación

### 5. Interfaz Mejorada
- Menú dedicado: **Contabilidad → Xtendoo → Líneas de extracto (edición total)**
- Vista tree editable en línea
- Vista form organizada por secciones:
  - Información General
  - Importe y Moneda
  - Diario y Extracto
  - Conciliación
  - Auditoría y Ajuste Manual
- Smart buttons para navegación rápida
- Badges visuales de estado (conciliada, posteada, pendiente)

## Instalación

1. Copiar el módulo en la carpeta de addons de Xtendoo
2. Actualizar la lista de módulos
3. Instalar el módulo `account_banck_statement_line`

## Configuración

### Activar/Desactivar Edición Total

El módulo incluye un parámetro de sistema que controla si la edición total está habilitada:

**Ruta**: Configuración → Técnico → Parámetros → Parámetros del Sistema

**Clave**: `account_banck_statement_line.allow_full_edit`

**Valor**: `True` (activado) / `False` (desactivado)

Cuando está desactivado, las vistas vuelven al comportamiento estándar de solo lectura.

### Asignar Permisos

1. Ir a **Configuración → Usuarios y Compañías → Grupos**
2. Buscar el grupo: "Xtendoo - Editor líneas de extracto"
3. Añadir los usuarios autorizados
4. **Nota**: Los usuarios con el rol "Asesor" (`account.group_account_manager`) tienen acceso automático

## Uso

### Acceder a las Líneas de Extracto

1. Navegar a: **Contabilidad → Xtendoo → Líneas de extracto (edición total)**
2. Se mostrará la lista de todas las líneas de extracto bancario
3. Hacer clic en una línea para editarla o usar la edición en línea

### Editar una Línea

1. Abrir la línea desde la vista tree o form
2. Si la línea está conciliada o posteada, aparecerá un banner de advertencia
3. Si es necesario, aparecerá un wizard de confirmación explicando los riesgos
4. Modificar los campos necesarios
5. **Importante**: Rellenar el campo "Motivo del ajuste manual" para documentar el cambio
6. Guardar los cambios

### Recalcular Totales

Si después de editar campos se produce un descuadre:

1. Usar el botón "Recalcular totales/conciliación" en el formulario
2. El sistema recomputará los valores dependientes
3. Verificar que los totales cuadran

## Advertencias y Limitaciones

### ⚠️ Advertencias Importantes

- **Impacto Contable**: Editar líneas conciliadas o posteadas puede afectar la contabilidad
- **Integridad**: Siempre documentar el motivo del ajuste en el campo correspondiente
- **Validación**: Después de ediciones masivas, verificar que los totales del extracto cuadran
- **Auditoría**: Todos los cambios quedan registrados en el chatter con usuario y timestamp

### Limitaciones Técnicas

Los siguientes campos permanecen de solo lectura por ser técnicos:

- `id`: ID interno del registro
- `create_date`: Fecha de creación
- `create_uid`: Usuario creador
- `write_date`: Fecha de última modificación
- `write_uid`: Usuario que modificó

Algunos campos compute sin inverse pueden no ser editables directamente. En estos casos:
- Se documenta en el código la razón
- Se proporciona alternativa mediante campos relacionados cuando es posible

## Estructura del Módulo

```
account_banck_statement_line/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   └── account_bank_statement_line.py
├── views/
│   ├── account_bank_statement_line_views.xml
│   └── menus.xml
├── security/
│   ├── security.xml
│   └── ir.model.access.csv
├── wizard/
│   ├── __init__.py
│   ├── edit_confirm_wizard.py
│   └── edit_confirm_wizard_views.xml
├── data/
│   └── ir_config_parameter.xml
├── demo/
│   └── demo_statement.xml
└── static/
    └── description/
        ├── icon.png
        └── index.html
```

## Tests

El módulo incluye tests unitarios que verifican:

1. ✓ Usuarios sin grupo no pueden editar
2. ✓ Usuarios con grupo sí pueden editar todos los campos
3. ✓ Edición en estado "posteado" requiere confirmación y deja trazabilidad
4. ✓ Botón de recálculo no rompe integridad

Para ejecutar los tests:

```bash
odoo-bin -c odoo.conf -d test_db -i account_banck_statement_line --test-enable --stop-after-init
```

## Soporte

Para soporte, contactar con:

**Xtendoo Software S.L.U.**
- Web: https://www.xtendoo.es
- Email: info@xtendoo.es

## Licencia

LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)

## Créditos

### Autores

- Xtendoo Software S.L.U.

### Mantenedores

Este módulo es mantenido por Xtendoo Software S.L.U.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from . import models
from . import wizard
