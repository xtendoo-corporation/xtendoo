# xtendoo_pos_cash_move

Modulo para Odoo 19.0 orientado a calidad OCA para consultar e interactuar con movimientos de caja PoS de forma segura.

## Principios de diseno

- Sin duplicar datos: se apoya en modelos contables/PoS nativos.
- No modifica asientos publicados.
- Bloquea operaciones sobre sesiones cerradas.
- Si no hay metodo backend estandar y seguro para cash in/out, el wizard queda bloqueado con mensaje claro.

## Modelo origen de datos (a verificar en tu Odoo 19)

Este modulo usa como origen de datos lineas contables de extracto bancario vinculadas a la sesion PoS:
- `account.bank.statement.line` (relacionado con `pos.session` via campo de sesion/caja segun implementacion nativa).

## Metodo estandar para Cash In/Cash Out (a verificar en tu Odoo 19)

Antes de habilitar creacion real, verifica en codigo fuente si existe un metodo backend estandar en `pos.session` para registrar movimientos de caja.

Busqueda recomendada:
```bash
grep -RIn "cash in\|cash out\|statement line\|bank statement" odoo/auto/addons/point_of_sale/models
grep -RIn "class PosSession\|def .*cash\|def .*statement" odoo/auto/addons/point_of_sale/models
```

Si no se encuentra una API backend segura/documentada, el wizard debe permanecer en modo bloqueado (comportamiento por defecto de este modulo).

