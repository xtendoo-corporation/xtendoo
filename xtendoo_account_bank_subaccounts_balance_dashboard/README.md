# Account Bank Subaccounts Balance Dashboard

## Descripción

Este módulo para Odoo 18.0 muestra el saldo total de las subcuentas bancarias en el panel del tablero (dashboard) de Contabilidad.

En cada tarjeta de diario tipo "Banco" (`account.journal` type = 'bank'), justo debajo del saldo principal del diario ("Saldo"), se muestra una línea adicional con el texto:

**"Saldo de subcuentas: <importe>"**

## Funcionalidad

### Cálculo de la cuenta principal
Para cada diario de banco, la cuenta principal se obtiene con la siguiente prioridad:
1. `journal.default_account_id` si existe y es de tipo liquidez (`asset_cash`)
2. `journal.payment_debit_account_id`
3. `journal.payment_credit_account_id`

### Definición de subcuentas
Las subcuentas se definen como todas las cuentas cuyo código comienza con el código de la cuenta principal, excluyendo la cuenta principal misma.

Por ejemplo, si la cuenta principal es `572`, las subcuentas serían `5720`, `5721`, `57200`, etc.

### Cálculo del saldo
- Solo se consideran movimientos posteados (`move_id.state = 'posted'`)
- Solo de la misma compañía del diario (`company_id`)
- Saldo en moneda de compañía (usando `balance = debit - credit`)

### Performance
- Utiliza `read_group` para calcular los saldos de forma eficiente
- Los datos se calculan en batch para todos los diarios

### Multi-compañía
- Respeta siempre el `company_id` del journal

## Visualización

- El saldo de subcuentas se muestra solo si el diario es tipo banco
- Solo se muestra si existe cuenta principal y hay subcuentas
- Si no hay subcuentas, no se muestra nada
- El texto se muestra en estilo sutil (tamaño menor, color muted)

## Dependencias

- `account`

## Autor

- Xtendoo (https://xtendoo.es)

## Licencia

LGPL-3
