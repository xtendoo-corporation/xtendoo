# Account Move Sequence Fix

## Descripción

Este módulo soluciona un problema crítico en Odoo 17 donde al validar facturas se produce un error de PostgreSQL:

```
psycopg2.errors.UndefinedFunction: operator does not exist: integer = boolean
LINE 1: SELECT number_next FROM ir_sequence WHERE id=false FOR UPDAT...
```

El error ocurre cuando el campo `secure_sequence_id` de un diario contiene un valor booleano `false` en lugar de un ID de secuencia válido.

## Problema

Cuando se intenta validar una factura, el sistema intenta obtener el siguiente número de secuencia ejecutando:

```sql
SELECT number_next FROM ir_sequence WHERE id=false FOR UPDATE NOWAIT
```

Esto causa un error porque PostgreSQL no puede comparar un campo `integer` (id) con un valor `boolean` (false).

## Solución

Este módulo añade validaciones en dos niveles:

1. **En el modelo `ir.sequence`**: Valida que el ID de la secuencia sea válido antes de ejecutar consultas SQL.

2. **En el modelo `account.move`**: Valida las secuencias del diario antes de validar el movimiento contable y proporciona mensajes de error claros al usuario.

## Instalación

1. Coloca el módulo en el directorio de addons personalizado
2. Actualiza la lista de módulos
3. Instala el módulo "Account Move Sequence Fix"

## Uso

Una vez instalado, el módulo:

- Detecta automáticamente secuencias inválidas en diarios
- Intenta recargar las secuencias para obtener datos válidos
- Muestra mensajes de error claros si no se puede resolver el problema
- Previene que se validen facturas con configuraciones inválidas

## Diagnóstico

Si encuentras el error, ejecuta estas consultas SQL para diagnosticar:

```sql
-- Verificar diarios con secuencias inválidas
SELECT
    aj.id,
    aj.name,
    aj.code,
    aj.secure_sequence_id
FROM account_journal aj
WHERE aj.secure_sequence_id IS NOT NULL
  AND aj.secure_sequence_id NOT IN (SELECT id FROM ir_sequence);

-- Corregir diarios con secuencias inválidas
UPDATE account_journal
SET secure_sequence_id = NULL
WHERE secure_sequence_id NOT IN (SELECT id FROM ir_sequence);
```

## Autor

**Xtendoo**
- Website: https://www.xtendoo.es

## Licencia

AGPL-3

## Mantenimiento

Este módulo es mantenido por Xtendoo.

