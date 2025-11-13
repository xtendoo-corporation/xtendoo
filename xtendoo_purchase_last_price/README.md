# Paniagua - Actualizar Precio de Compra desde Última Compra

## Descripción

Este módulo actualiza automáticamente el precio de coste (standard_price) de los productos en su ficha basándose en el último precio de compra realizado.

## Funcionalidad

### 🔄 Actualización Automática del Coste y Precio del Proveedor

Cada vez que se **confirma un pedido de compra**, el sistema realiza automáticamente dos actualizaciones:

1. **Actualiza el precio de coste del producto** (standard_price) con el precio unitario de la compra
2. **Actualiza o crea el precio en la lista del proveedor** (product.supplierinfo) para ese producto y proveedor

### 📋 Cuándo se actualiza el coste:

1. **Al confirmar un pedido de compra**: Todos los productos del pedido actualizan su coste
2. **Al modificar el precio en un pedido confirmado**: Si cambias el precio de una línea en un pedido ya confirmado, se actualiza el coste
3. **Al agregar líneas a un pedido confirmado**: Si agregas productos a un pedido ya confirmado, se actualiza su coste

### 🎯 Características:

- ✅ **Actualización del coste del producto**: Mantiene el coste actualizado con el último precio de compra
- ✅ **Actualización del precio del proveedor**: Actualiza automáticamente la lista de precios del proveedor en la ficha del producto
- ✅ **Creación automática**: Si no existe una línea de proveedor, la crea automáticamente
- ✅ **Conversión de UdM**: Si la unidad de medida de compra es diferente a la del producto, se convierte automáticamente
- ✅ **Logging**: Cada actualización queda registrada en los logs con el precio anterior y el nuevo
- ✅ **Automático**: No requiere intervención del usuario
- ✅ **Transparente**: El coste se actualiza sin afectar valoraciones de stock existentes

## Funcionamiento

### Ejemplo:

1. **Producto**: Mesa de madera
   - Coste actual: 50.00 €
   - Proveedor "Muebles SA" tiene precio: 48.00 €

2. **Nueva compra**: Creas un pedido de compra a "Muebles SA"
   - Producto: Mesa de madera
   - Precio unitario: 55.00 €

3. **Al confirmar el pedido**:
   - ✅ El coste del producto se actualiza automáticamente a 55.00 €
   - ✅ El precio del proveedor "Muebles SA" se actualiza a 55.00 €
   - 📝 Queda registrado en los logs:
     - "Actualizado coste del producto 'Mesa de madera' de 50.00 a 55.00"
     - "Actualizado precio del proveedor 'Muebles SA' para producto 'Mesa de madera': 48.00 → 55.00"

4. **Siguiente compra a otro proveedor**:
   - Si compras el mismo producto a "Proveedor XYZ" por 52.00 €
   - Al confirmar:
     - ✅ El coste del producto se actualiza a 52.00 €
     - ✅ Se crea una nueva línea de proveedor para "Proveedor XYZ" con precio 52.00 €
     - ℹ️ El precio de "Muebles SA" permanece en 55.00 € (cada proveedor mantiene su propio precio)

## Consideraciones

- El módulo actualiza el campo `standard_price` del producto (coste)
- Actualiza o crea registros en `product.supplierinfo` (lista de precios del proveedor)
- Cada proveedor mantiene su propio precio en la ficha del producto
- Solo actualiza cuando el precio de compra es mayor a 0
- Si la compra tiene una UdM diferente a la del producto, convierte el precio automáticamente
- Los pedidos en borrador NO actualizan hasta que se confirman
- El contexto `disable_auto_svl` previene la creación automática de movimientos de valoración
- Si no existe una línea de proveedor para ese producto, se crea automáticamente con el precio de la compra

## Instalación

1. Instalar el módulo
2. No requiere configuración adicional
3. Funciona automáticamente desde el momento de la instalación

## Dependencias

- `purchase`: Módulo de compras de Odoo
- `stock`: Módulo de inventario de Odoo

## Autor

Xtendoo - https://www.xtendoo.es

## Licencia

AGPL-3

