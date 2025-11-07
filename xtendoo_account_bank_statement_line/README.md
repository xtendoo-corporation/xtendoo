# Xtendoo Account Bank Statement Line Editor

## Descripción

Este módulo proporciona una interfaz completa para ver y editar todos los campos de las líneas de extracto bancario (`account.bank.statement.line`).

## Características

- **Vista Tree completa**: Visualiza todas las líneas de extracto bancario con los campos más importantes.
- **Vista Form detallada**: Permite ver y editar todos los campos de una línea de extracto bancario.
- **Verificación de Running Balance**: Permite verificar que el campo `running_balance` está correctamente calculado.
- **Filtros y agrupaciones**: Búsqueda avanzada con múltiples filtros y opciones de agrupación.

## Campos principales visibles

### Vista Tree
- Fecha
- Referencia de pago
- Partner
- Nombre del partner
- Diario
- Extracto
- Importe
- **Running Balance** (Saldo acumulado)
- Estado de conciliación
- Estado del movimiento

### Vista Form
El formulario está organizado en las siguientes secciones:

1. **Información Principal**
   - Fecha
   - Referencia de pago
   - Partner
   - Nombre del partner
   - Número de cuenta bancaria
   - Tipo de transacción
   - Estado de conciliación

2. **Importes**
   - Importe
   - Moneda
   - **Running Balance** (destacado)
   - Importe residual
   - Moneda extranjera
   - Importe en moneda extranjera

3. **Información del Extracto**
   - Extracto
   - Nombre del extracto
   - Extracto completo
   - Extracto válido
   - Saldo final real del extracto

4. **Diario y Compañía**
   - Diario
   - Compañía
   - Código de país

5. **Información Técnica**
   - Movimiento contable (Journal Entry)
   - Índice interno
   - Secuencia

6. **Información de Pago**
   - Pagos asociados

### Pestañas adicionales
- **Transaction Details**: Detalles de la transacción en formato JSON
- **Journal Entry**: Líneas del movimiento contable asociado

## Acceso

El módulo añade un nuevo menú en:
**Contabilidad > Asientos Contables > Bank Statement Lines**

## Permisos

- **Usuario de Contabilidad**: Lectura solamente
- **Facturación**: Lectura y escritura
- **Gestor de Contabilidad**: Acceso completo (lectura, escritura, creación, eliminación)

## Uso

1. Instala el módulo desde Apps
2. Ve a Contabilidad > Asientos Contables > Bank Statement Lines
3. La vista tree mostrará todas las líneas de extracto bancario
4. Haz clic en cualquier línea para ver todos sus campos en detalle
5. Verifica que el campo **Running Balance** está correctamente calculado comparándolo con los importes acumulados

## Verificación del Running Balance

El campo `running_balance` representa el saldo acumulado en la cuenta bancaria. Este módulo te permite:
- Ver el running balance de cada línea en la vista tree
- Comparar el running balance entre líneas consecutivas
- Verificar que la diferencia entre running balances consecutivos coincide con el importe de la línea
- Detectar posibles inconsistencias en el cálculo

## Autor

**Xtendoo** - https://www.xtendoo.es

## Licencia

AGPL-3.0

## Versión

17.0.1.0.0

