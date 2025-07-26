# POS UoM Selection

## Descripción

Este módulo permite a los usuarios del POS de Odoo seleccionar diferentes unidades de medición para los productos durante la venta. Solo se pueden seleccionar unidades de medición que pertenezcan a la misma categoría que la unidad base del producto.

## Características

- **Selección de UoM en POS**: Los usuarios pueden cambiar la unidad de medición de cualquier producto directamente desde la interfaz del POS.
- **Filtrado por categoría**: Solo se muestran unidades de medición compatibles (de la misma categoría).
- **Configuración por tienda**: Se puede habilitar o deshabilitar la funcionalidad por configuración de POS.
- **Interfaz intuitiva**: Popup fácil de usar con información de conversión entre unidades.
- **Información visual**: Muestra el tipo de unidad (base, mayor, menor) y factores de conversión.

## Instalación

1. Copiar el módulo en la carpeta de addons de Odoo
2. Actualizar la lista de módulos
3. Instalar el módulo "POS UoM Selection"

## Configuración

1. Ir a **Punto de Venta > Configuración > Configuraciones de POS**
2. Seleccionar la configuración deseada
3. En la sección "Gestión de Productos", activar **"Permitir selección de UdM"**
4. Guardar la configuración

## Uso

### En el POS

1. **Desde la pantalla de productos**: Hacer clic en el botón "Cambiar" junto a la información de UoM del producto
2. **Desde las líneas de pedido**: Hacer clic en el botón con el icono de balanza junto al nombre de la unidad de medición
3. **Selección**: Elegir la unidad de medición deseada del popup que aparece
4. **Confirmación**: Confirmar la selección para aplicar el cambio

### Popup de Selección

El popup muestra:
- Nombre de la unidad de medición
- Categoría de la unidad
- Tipo de unidad (Base, Mayor, Menor)
- Información de conversión entre unidades

## Requisitos Técnicos

- Odoo 18.0
- Módulo `point_of_sale`
- Módulo `uom`

## Licencia

AGPL-3.0

## Autor

Xtendoo - https://www.xtendoo.es
