# Xtendoo Company Required

## Descripción

Este módulo extiende la funcionalidad de Odoo para asegurar que:

1. Los productos siempre tengan una empresa asignada
2. Los contactos (partners) mantengan consistencia entre su empresa y las ubicaciones de stock asignadas

## Funcionalidades

### 1. Validación de Empresa en Productos
- Previene la creación de productos sin empresa asignada
- Previene la eliminación de la empresa de un producto existente

### 2. Validación de Ubicaciones de Stock en Contactos

El módulo previene inconsistencias como:
- Un partner que pertenece a la empresa "A" pero tiene ubicaciones de stock de la empresa "B"
- Garantiza que `property_stock_customer` y `property_stock_supplier` sean consistentes con la empresa del partner

### 3. Corrección Automática

#### Migración Automática
Al actualizar a la versión 19.0.1.0.2, el módulo ejecuta automáticamente un script de migración que:
- Identifica todos los partners con inconsistencias
- Corrige las ubicaciones de stock para que coincidan con la empresa del partner
- Registra en el log todos los cambios realizados

#### Corrección Manual
Los usuarios pueden corregir manualmente los partners de dos formas:

1. **Desde el formulario de contacto**:
   - Un botón "Corregir Ubicaciones de Stock" aparece cuando el contacto tiene empresa asignada

2. **Desde la vista de lista**:
   - Seleccionar uno o varios contactos
   - Usar la acción "Corregir Ubicaciones de Stock" del menú contextual

### 4. Actualización Automática
Cuando se cambia la empresa de un partner, el módulo actualiza automáticamente las ubicaciones de stock para mantener la consistencia.

## Instalación

1. Copiar el módulo en la carpeta de addons
2. Actualizar la lista de módulos
3. Instalar el módulo "Xtendoo Company Required"

## Actualización

Si ya tienes una versión anterior instalada:

1. Actualizar el código del módulo
2. Actualizar el módulo desde Odoo:
   ```bash
   # Desde la línea de comandos
   odoo-bin -u xtendoo_company_required -d nombre_base_datos
   ```
3. El script de migración se ejecutará automáticamente y corregirá las inconsistencias existentes

## Solución de Problemas

### Error: "company inconsistencies here"

Este error aparece cuando hay inconsistencias entre la empresa del partner y las ubicaciones de stock. Para solucionarlo:

1. **Opción 1 - Actualizar el módulo**: La migración automática lo resolverá
2. **Opción 2 - Corrección manual**: Usar el botón o acción de corrección en los contactos afectados
3. **Opción 3 - Por código**: Ejecutar en la consola de Odoo:
   ```python
   partners = env['res.partner'].search([('company_id', '!=', False)])
   for partner in partners:
       partner.action_fix_stock_locations()
   ```

## Notas Técnicas

- El módulo añade constraints a nivel de modelo para prevenir futuras inconsistencias
- Las validaciones se ejecutan al crear o modificar partners
- Las ubicaciones de stock se asignan según la empresa del partner
- Si no existen ubicaciones específicas para una empresa, se usan las ubicaciones sin empresa asignada

## Dependencias

- `product`
- `point_of_sale`
- `stock`

## Autor

Manuel Calero Solis (Xtendoo)

## Licencia

AGPL-3

