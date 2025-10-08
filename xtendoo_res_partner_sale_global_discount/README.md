# Xtendoo - Descuentos Globales de Cliente

## Descripción

Este módulo permite gestionar descuentos globales por cliente que se aplican automáticamente en presupuestos, pedidos y facturas de venta.

## Características

- **Configuración de descuentos por cliente**: Cada cliente puede tener múltiples descuentos configurados
- **Tipos de descuento**: Porcentaje o importe fijo
- **Criterios de aplicación**: Fechas de validez, importe mínimo, tipo de documento
- **Aplicación automática**: Los descuentos se pueden aplicar automáticamente al cambiar de cliente
- **Aplicación manual**: Botón disponible en presupuestos, pedidos y facturas
- **Secuenciación**: Los descuentos se aplican en orden de secuencia configurado

## Instalación

1. Copiar el módulo en el directorio de addons
2. Actualizar la lista de módulos
3. Instalar el módulo "Xtendoo - Descuentos Globales de Cliente"

## Uso

### Configuración de Descuentos

1. Ir a la ficha de un cliente (Ventas > Clientes)
2. Abrir la pestaña "Descuentos Globales"
3. Añadir los descuentos deseados con sus criterios

### Aplicación en Documentos

Los descuentos se pueden aplicar de dos formas:

1. **Automáticamente**: Al seleccionar un cliente con descuentos configurados
2. **Manualmente**: Usando el botón "Aplicar Descuentos Globales" en presupuestos, pedidos y facturas

### Campos de Configuración

- **Nombre**: Descripción del descuento
- **Tipo**: Porcentaje (0-100) o Importe Fijo
- **Valor**: Porcentaje o importe según el tipo
- **Fechas**: Período de validez del descuento
- **Importe Mínimo**: Importe mínimo del documento para aplicar el descuento
- **Aplicar a**: Tipo de documento (todos, presupuestos, pedidos, facturas)
- **Secuencia**: Orden de aplicación cuando hay múltiples descuentos

## Autor

Xtendoo - Versión 18.0.1.0.0
