# Alerta de Venta - Pagos Vencidos

## Descripción

Este módulo proporciona alertas visuales para clientes con facturas vencidas en los pedidos de venta de Odoo 17.0.

## Funcionalidades

### Banner de Alerta en Pedidos de Venta
- Muestra un banner rojo prominente en la cabecera del pedido de venta
- Se activa automáticamente cuando el cliente seleccionado tiene facturas vencidas
- Incluye información detallada:
  - Nombre del cliente
  - Número de facturas vencidas
  - Importe total vencido
- Botón para ver las facturas vencidas directamente

### Detección Automática
- Detecta automáticamente facturas vencidas basándose en:
  - Facturas en estado "Publicado"
  - Estado de pago "No pagado" o "Parcialmente pagado"
  - Fecha de vencimiento anterior a la fecha actual
- Considera todas las facturas del partner comercial (empresa matriz)

## Instalación

1. Coloca el módulo en el directorio de addons de Xtendoo
2. Actualiza la lista de módulos
3. Instala el módulo "Alerta de Venta - Pagos Vencidos"

## Uso

1. **Banner de Alerta**:
   - Abre cualquier pedido de venta
   - Selecciona un cliente con facturas vencidas
   - El banner aparecerá automáticamente en la parte superior del formulario
   - Haz clic en "Ver Facturas Vencidas" para revisar las facturas pendientes

## Configuración

No se requiere configuración adicional. El módulo funciona automáticamente una vez instalado.

## Compatibilidad

- Odoo 17.0
- Compatible con los módulos estándar de Ventas y Contabilidad

## Soporte

Desarrollado por Xtendoo
Sitio web: https://xtendoo.es
