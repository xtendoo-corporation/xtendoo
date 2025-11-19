# Guía de Instalación y Uso - Xtendoo POS Order Backend

## 📦 INSTALACIÓN

### Paso 1: Verificar el módulo en el sistema

El módulo debe estar ubicado en:
```
/odoo/custom/src/xtendoo/xtendoo_pos_order/
```

### Paso 2: Actualizar lista de aplicaciones

1. Acceda a Odoo como administrador
2. Active el **Modo Desarrollador**:
   - Vaya a **Ajustes**
   - En la parte inferior, haga clic en **Activar el modo desarrollador**
3. Vaya a **Aplicaciones**
4. Haga clic en el menú (☰) y seleccione **Actualizar lista de aplicaciones**
5. Confirme la actualización

### Paso 3: Instalar el módulo

1. En **Aplicaciones**, elimine el filtro "Aplicaciones" de la búsqueda
2. Busque: `xtendoo_pos_order`
3. Haga clic en **Instalar**
4. Espere a que la instalación complete

---

## ⚙️ CONFIGURACIÓN

### Configurar un Punto de Venta en modo Backend

#### Paso 1: Acceder a la configuración del POS

1. Vaya a **Punto de Venta** → **Configuración** → **Puntos de Venta**
2. Seleccione el punto de venta que desea configurar (o cree uno nuevo)

#### Paso 2: Seleccionar el tipo de interfaz

1. En el formulario del punto de venta, busque la sección **Interface Configuration**
2. Seleccione una de las opciones:
   - **Standard POS Frontend**: Interfaz JavaScript tradicional (por defecto)
   - **Backend Orders Interface**: Gestión desde el backend ✓
3. Guarde los cambios

#### Paso 3: Configurar otras opciones del POS

Asegúrese de configurar:
- **Lista de precios** (Pricelist)
- **Diario de pagos** (Payment Methods)
- **Cliente por defecto** (opcional)
- **Secuencia de órdenes**

---

## 🚀 USO DEL MÓDULO

### Método 1: Abrir desde el botón del POS

#### Paso 1: Abrir sesión

1. Vaya a **Punto de Venta** → **Configuración** → **Puntos de Venta**
2. Localice el POS configurado en modo "Backend Orders Interface"
3. Haga clic en el botón de la caja para abrirla

#### Paso 2: Gestionar sesión

- Si no hay sesión abierta, el sistema le pedirá abrir una
- Si ya hay una sesión abierta, se abrirá directamente la vista de órdenes

#### Paso 3: Vista de órdenes

Se abrirá automáticamente la vista de lista de órdenes POS filtrada por esta caja.

---

### Método 2: Acceso desde el menú directo

1. Vaya a **Punto de Venta** → **Órdenes Backend**
2. Use los filtros para seleccionar el punto de venta deseado
3. Las órdenes se mostrarán en vista de lista

---

## 📝 CREAR UNA ORDEN DE POS

### Paso 1: Crear nueva orden

1. Desde la vista de órdenes, haga clic en **Crear**
2. Se abrirá el formulario de nueva orden

### Paso 2: Completar información básica

**Campos obligatorios:**
- **Punto de Venta** (config_id): Seleccione el POS
- **Sesión** (session_id): Seleccione la sesión abierta

**Campos opcionales:**
- **Cliente** (partner_id): Cliente de la venta
- **Lista de precios**: Se toma del POS por defecto
- **Posición fiscal**: Para gestión de impuestos
- **Vendedor**: Usuario que realiza la venta

### Paso 3: Agregar productos

1. En la pestaña **Líneas de orden**, haga clic en **Agregar una línea**
2. Seleccione el **Producto**
3. Se auto-completará:
   - Precio unitario (desde la lista de precios)
   - Impuestos aplicables
4. Especifique:
   - **Cantidad** (qty)
   - **Descuento** (opcional)
5. Los subtotales se calcularán automáticamente

**Repita** para agregar más productos.

### Paso 4: Verificar totales

Los siguientes campos se calculan automáticamente:
- Subtotal sin impuestos
- Total de impuestos
- Total de la orden

### Paso 5: Registrar pagos

1. Vaya a la pestaña **Pagos**
2. Haga clic en **Agregar una línea**
3. Seleccione el **Método de pago**
4. Ingrese el **Monto**
5. Repita si hay múltiples formas de pago

**Importante:** El total de pagos debe cubrir o exceder el total de la orden.

### Paso 6: Confirmar la orden

1. Haga clic en el botón **Marcar como Pagado**
2. La orden cambiará su estado a "Paid" (Pagado)

### Paso 7: Generar factura (opcional)

Si necesita generar una factura:
1. Asegúrese de que la orden tenga un **Cliente** asignado
2. Haga clic en el botón **Crear Factura**
3. Se generará automáticamente la factura asociada

---

## 🔍 CASOS DE USO COMUNES

### Caso 1: Venta mostrador sin pantalla táctil

**Escenario:** Tiene un mostrador con PC tradicional sin pantalla táctil.

**Solución:**
1. Configure el POS en modo "Backend Orders Interface"
2. El personal puede usar mouse y teclado para crear órdenes
3. Misma funcionalidad que el POS, pero con interfaz familiar

### Caso 2: Órdenes telefónicas

**Escenario:** Recibe pedidos por teléfono que deben registrarse como ventas POS.

**Solución:**
1. Desde el backoffice, abra **Punto de Venta → Órdenes Backend**
2. Cree una nueva orden con los datos del cliente
3. Agregue los productos solicitados
4. Registre el pago (puede ser pago diferido)
5. Genere la factura si es necesario

### Caso 3: Integración con flujo ERP

**Escenario:** Necesita integrar ventas mostrador con el flujo normal de pedidos.

**Solución:**
1. Use el modo backend para crear órdenes POS con el mismo flujo que pedidos de venta
2. Las órdenes se comportan como POS pero se gestionan como pedidos normales
3. Facilita la integración con otros módulos (inventario, contabilidad, etc.)

---

## ⚠️ VALIDACIONES Y RESTRICCIONES

### Creación de órdenes

- ✓ Solo se pueden crear órdenes manualmente cuando el POS está en modo "Backend"
- ✓ Si intenta crear una orden en un POS configurado como "Frontend", recibirá un error
- ✓ Las órdenes creadas desde el frontend JS del POS siempre funcionan, independientemente del modo

### Sesiones

- ✓ Debe existir una sesión abierta para crear órdenes
- ✓ Si no hay sesión abierta, el sistema mostrará un error indicando cómo abrir una

### Pagos

- ✓ El total de pagos debe cubrir el total de la orden
- ✓ Si intenta marcar como pagado sin pagos suficientes, recibirá un error

### Facturas

- ✓ Solo puede generar factura si la orden tiene un cliente asignado
- ✓ No se puede generar factura para órdenes en borrador o canceladas

---

## 🔐 PERMISOS

### Roles necesarios

Para trabajar con órdenes POS desde el backend, los usuarios necesitan:

- **Mínimo:** `Usuario de Punto de Venta` (Point of Sale / User)
- **Recomendado:** `Administrador de Punto de Venta` (Point of Sale / Manager)

### Asignar permisos

1. Vaya a **Ajustes** → **Usuarios y Compañías** → **Usuarios**
2. Seleccione el usuario
3. En la pestaña **Derechos de acceso**
4. En la sección **Punto de Venta**, seleccione:
   - **Usuario**: Para crear y editar órdenes
   - **Administrador**: Para configuración completa

---

## 🐛 SOLUCIÓN DE PROBLEMAS

### Error: "No se permite crear órdenes manualmente"

**Causa:** El POS está configurado en modo "Frontend".

**Solución:**
1. Vaya a la configuración del POS
2. Cambie **Interface Type** a "Backend Orders Interface"

### Error: "No hay ninguna sesión abierta"

**Causa:** No existe una sesión activa para el POS.

**Solución:**
1. Vaya a **Punto de Venta → Configuración → Puntos de Venta**
2. Seleccione el POS
3. Haga clic en **Abrir Sesión**

### Error: "El total de pagos no cubre el total de la orden"

**Causa:** Los pagos registrados son menores al total.

**Solución:**
1. Vaya a la pestaña **Pagos** de la orden
2. Agregue pagos adicionales hasta cubrir el total
3. Intente marcar como pagado nuevamente

### No aparece el botón "Crear"

**Causa:** Puede estar viendo la vista sin permisos adecuados.

**Solución:**
1. Verifique que tiene rol de "Usuario de Punto de Venta" o superior
2. Actualice la página
3. Si persiste, verifique que el módulo esté correctamente instalado

### Los totales no se calculan

**Causa:** Puede faltar información en las líneas de productos.

**Solución:**
1. Verifique que cada línea tenga:
   - Producto seleccionado
   - Cantidad mayor a 0
   - Precio unitario
2. Los impuestos deben estar configurados en el producto
3. Guarde la orden para recalcular

---

## 📞 SOPORTE

Para soporte técnico o consultas adicionales:

**Xtendoo**
- Web: https://www.xtendoo.es
- Email: Contacte con su representante de Xtendoo

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

Use este checklist para una implementación exitosa:

- [ ] Módulo instalado correctamente
- [ ] Modo desarrollador activado (para configuración inicial)
- [ ] Punto de Venta creado/configurado
- [ ] Interface Type configurado como "Backend Orders Interface"
- [ ] Lista de precios asignada al POS
- [ ] Métodos de pago configurados
- [ ] Productos marcados como "Available in POS"
- [ ] Sesión de POS abierta
- [ ] Usuarios con permisos adecuados
- [ ] Prueba de creación de orden exitosa
- [ ] Verificación de cálculos de totales
- [ ] Prueba de generación de factura
- [ ] Documentación entregada al equipo

---

**¡Listo para usar Xtendoo POS Order Backend!** 🎉

