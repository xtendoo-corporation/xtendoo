======================================
Xtendoo - Informe de ventas diarias TPV
======================================

Rediseña el informe estándar de ventas diarias (X/Z) del Punto de Venta
para que el cierre de caja ofrezca una visión general de la sesión.

Cambios respecto al informe estándar
====================================

* **Resumen de la sesión** al principio: total vendido, número de
  tickets, ticket medio, base imponible, impuestos y, si las hay,
  devoluciones.
* **Cobros por forma de pago**, justo después del resumen: una fila por
  forma de pago (todas las sesiones agregadas) con el número de cobros,
  el importe y el porcentaje sobre el total, y una fila de total
  cobrado. El cambio devuelto en efectivo descuenta importe pero no
  cuenta como un cobro.
* **Ventas por producto**: una sola línea por producto, ordenadas por
  nombre, con referencia, cantidad, base e importe con impuestos. Se
  eliminan los códigos de barras y la agrupación por categoría, y los
  nombres largos se recortan para no ocupar más de una línea.
* **Devoluciones por producto** con el mismo formato.
* **Facturas**: en lugar de la relación de todas las facturas, se
  muestra el número de facturas, la primera y la última, y el total.

El resto de secciones (impuestos, descuentos y control de la sesión) se
mantienen como en el estándar.

Alcance
=======

El cambio se aplica a todos los puntos donde Odoo genera este informe:
la impresión desde el TPV (botón de detalle de ventas y cierre de
caja), el asistente *Punto de venta > Informes > Detalles de ventas* y
el PDF adjunto al email de cierre de
``xtendoo_pos_session_close_email``.

Se conservan los identificadores de las secciones estándar
(``payments``, ``sales``, ``refunds``, ``invoices``) para que otros
módulos que extienden el informe sigan funcionando.

Limitaciones
============

Los importes nuevos se calculan en la moneda de los pedidos, sin
conversión entre monedas; está pensado para puntos de venta que operan
en una única moneda.
