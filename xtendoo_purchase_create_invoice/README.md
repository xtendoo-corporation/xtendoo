# Xtendoo Purchase Create Invoice

Este módulo permite crear facturas de compra directamente desde el pedido a proveedor con un solo clic, sin necesidad de subir documentos ni pasar por wizards.

## Características

- **Un Solo Clic**: El botón "Crear Factura" crea la factura inmediatamente, sin wizards ni intervención del usuario.
- **Automático**: Factura automáticamente las cantidades pendientes (recibidas pero no facturadas).
- **Sin Documentos**: No requiere subir ningún documento del proveedor.
- **Sin Wizards**: Proceso directo y rápido.
- **Inteligente**: Sabe qué hacer automáticamente.
- **Compatible**: Mantiene la compatibilidad con el flujo estándar de Odoo 19.0.

## Instalación

1. Copiar el módulo en la carpeta de addons personalizados.
2. Actualizar la lista de módulos.
3. Instalar el módulo "Xtendoo Purchase Create Invoice".

## Uso

### Uso Normal (100% de los casos)

1. Ir a un pedido de compra confirmado que tenga recepciones.
2. Hacer clic en el botón **"Crear Factura"**.
3. ✅ **¡Listo!** La factura se crea automáticamente.

**Eso es todo. No hay pasos adicionales.**

### ¿Qué hace exactamente?

- Crea una factura en estado borrador
- Incluye todas las líneas del pedido con cantidades pendientes de facturar
- Vincula la factura al pedido automáticamente
- Abre la factura para que puedas revisarla
- Registra un mensaje en el pedido confirmando la creación

## Ventajas vs. Flujo Estándar

| Odoo 19.0 Estándar | Con Este Módulo |
|--------------------|-----------------|
| ❌ Requiere subir documento | ✅ No requiere documento |
| ❌ Extracción de datos del documento | ✅ Datos directos del pedido |
| ❌ Múltiples pasos | ✅ Un solo clic |
| ❌ Requiere tener el PDF del proveedor | ✅ Funciona sin PDF |
| ~60 segundos | ~5 segundos |

## Notas Técnicas

- Extiende el modelo `purchase.order` con el método `action_create_invoice_direct()`
- Reemplaza el botón estándar "Crear Factura" por uno que funciona directamente
- Las facturas creadas se vinculan automáticamente al pedido de compra
- Compatible con Odoo 19.0
- Sin dependencias adicionales

## Autor

**Xtendoo**
- Website: https://xtendoo.es

## Licencia

AGPL-3



