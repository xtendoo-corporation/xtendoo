# Account Invoice Extract Fix

## Descripción

Este módulo corrige un error de JavaScript que ocurre al usar la función de extracción de facturas
con campos de distribución analítica en las líneas de factura.

## Problema Resuelto

Error: `TypeError: Cannot read properties of undefined (reading 'fields')`

Este error se produce cuando:
1. Se está usando el módulo `account_invoice_extract`
2. Se enfoca en un campo dentro de una relación x2many (como `analytic_distribution` en las líneas de factura)
3. El código intenta acceder a la configuración del campo padre que puede no estar inicializada

## Solución

El módulo aplica un parche al método `getBoxType` de `InvoiceExtractFormRenderer` para:
- Validar que el campo padre existe antes de acceder a su configuración
- Validar que `_config.fields` existe antes de intentar leer los campos
- Retornar `false` de forma segura cuando no se puede determinar el tipo de campo

## Instalación

1. Actualiza la lista de módulos en Odoo
2. Instala el módulo `Account Invoice Extract Fix`
3. El fix se aplicará automáticamente

## Dependencias

- account_invoice_extract

## Autor

Xtendoo - https://www.xtendoo.es

## Licencia

LGPL-3

