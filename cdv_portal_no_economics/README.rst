========================
Portal sin datos económicos
========================

Módulo puente que define un perfil de usuario de portal que **no puede ver ni
acceder** a los datos económicos: presupuestos, pedidos de venta, facturas
(incluidas las vencidas) y métodos de pago.

Funcionamiento
==============

Al instalar el módulo se crea el grupo de seguridad **"Portal sin datos
económicos"**. Los usuarios de portal a los que se les asigne ese grupo:

* No ven las tarjetas económicas en el portal (`/my`): *Presupuestos*,
  *Pedidos*, *Facturas*, *Facturas a pagar* y *Métodos de pago*.
* Son redirigidos a `/my` si intentan acceder por URL directa a cualquiera de
  las rutas económicas (`/my/quotes`, `/my/orders`, `/my/orders/<id>`,
  `/my/invoices`, `/my/invoices/<id>`, `/my/invoices/overdue`,
  `/my/payment_method`, `/payment/pay`).

El resto del portal (datos de contacto, direcciones, seguridad, etc.) sigue
disponible con normalidad.

Cómo crear el usuario de portal
===============================

1. En **Contactos**, abre el contacto y usa **Acción → Conceder acceso al
   portal**. Esto le asigna el grupo de portal estándar y envía la invitación.
2. En **Ajustes → Usuarios** (filtra por *Tipo de usuario = Portal*), edita el
   usuario y marca además el grupo **"Portal sin datos económicos"**.

Diseño
======

El módulo no modifica el core: hereda las plantillas estándar del portal para
ocultar cada tarjeta (localizándola por su `url` única) y extiende los
controladores para bloquear las rutas cuando el usuario pertenece al grupo. Es
aditivo y compatible con actualizaciones.
