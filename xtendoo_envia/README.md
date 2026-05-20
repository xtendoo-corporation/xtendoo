# Xtendoo Envia para Odoo 17

Guía simple para configurar el módulo `xtendoo_envia` paso a paso.

---

## 1. Qué hace este módulo

Este módulo conecta Odoo con **Envia.com** para poder:

- calcular tarifas de envío,
- generar envíos desde el albarán,
- obtener número de seguimiento,
- descargar etiquetas,
- cancelar envíos.

---

## 2. Antes de empezar

Necesitas tener:

- el módulo instalado,
- una cuenta en **Envia.com**,
- una **API Key de sandbox** y/o una **API Key de producción**,
- productos con **peso** configurado,
- direcciones de cliente y almacén bien completas.

---

## 3. Dónde se configura en Odoo

### Método de envío

Ve a:

- **Ventas > Configuración > Métodos de envío**

O también:

- **Inventario > Configuración > Delivery > Shipping Methods**

Abre el método de envío **Envia.com** o crea uno nuevo y en **Proveedor** elige **Envia**.

---

## 4. Configuración paso a paso

### Paso 1. Crear o abrir el método de envío

- Abre **Métodos de envío**.
- Crea uno nuevo o usa el que ya viene por defecto: **Envia.com**.
- En **Proveedor**, selecciona **Envia**.

### Paso 2. Elegir el entorno

En la parte superior del formulario verás el entorno:

- **Entorno de prueba** → usa la API key sandbox.
- **Producción** → usa la API key real.

Recomendación:

- empieza en **pruebas**,
- cuando todo funcione, cambia a **producción**.

### Paso 3. Poner las API Keys

En la pestaña **Configuración Envia**:

- pega tu **Envia Sandbox Access Token**,
- pega tu **Envia Production Access Token**.

No hace falta usar las dos al mismo tiempo, pero es recomendable dejar ambas configuradas.

### Paso 4. Configurar el paquete por defecto

En el campo **Envia Default Package** selecciona un tipo de paquete.

Puedes usar uno de estos que crea el módulo:

- **Envia Box**
- **Envia Envelope**
- **Envia Pallet**

Si necesitas crear uno nuevo:

Ve a:

- **Inventario > Configuración > Delivery > Package Types**

Y asegúrate de configurar:

- **Carrier Type** = `Envia`
- **Envia Package Type** = `box`, `envelope` o `pallet`
- largo, ancho y alto
- peso base y peso máximo si aplica

### Paso 5. Configurar país de origen

En el campo **Ship From** selecciona el país desde donde haces los envíos.

Normalmente será el país de tu empresa o almacén principal.

### Paso 6. Configurar moneda de la cuenta Envia

En **Envia Account Main Currency** elige la moneda principal con la que trabaja tu cuenta de Envia.

Ejemplo:

- `EUR`
- `USD`
- `MXN`

### Paso 7. Configurar formato de etiqueta

Configura:

- **Envia Label File Type** → normalmente `PDF`
- **Envia Label Type** → por ejemplo `PAPER_8.5X11`

Si imprimes en impresora térmica, revisa si necesitas `ZPL` o algún formato distinto.

### Paso 8. Sincronizar servicio de Envia

En **Envia.com Service Name** pulsa el icono de sincronización.

Esto hace que Odoo consulte Envia y te deje elegir:

- el **carrier**,
- el **servicio**.

Ejemplos:

- UPS
- DHL
- Estafeta
- Saver
- Express

Cuando elijas uno y confirmes, ese servicio quedará guardado en el método de envío.

> Importante: si no haces este paso, Odoo no podrá cotizar ni generar envíos.

### Paso 9. Revisar opciones especiales

Según el país y el tipo de paquete, pueden aparecer opciones como:

- devolución al remitente,
- entrega o recogida residencial,
- asistencia de montacargas.

Actívalas solo si realmente las necesitas.

---

## 5. Cómo probar que funciona

### Probar la tarifa

1. Crea un **pedido de venta**.
2. Añade productos con peso.
3. Pulsa **Agregar envío**.
4. Selecciona el método de envío de Envia.
5. Pulsa para actualizar coste.

Si todo está bien, Odoo devolverá una tarifa.

### Probar el envío real

1. Confirma el pedido.
2. Ve al **albarán**.
3. Reserva y valida cantidades.
4. Cuando el picking esté listo, usa **Enviar al transportista**.

Si todo está correcto:

- se genera el envío en Envia,
- se guarda el tracking,
- se adjunta la etiqueta en el chatter.

---

## 6. Errores típicos

### No aparecen servicios al sincronizar

Revisa:

- que la API key sea correcta,
- que el entorno sea el correcto,
- que en Envia tengas carriers activos,
- que el país de origen y el tipo de paquete sean válidos.

### No calcula tarifa

Revisa:

- que el método tenga servicio sincronizado,
- que los productos tengan peso,
- que el cliente tenga dirección completa,
- que el paquete tenga dimensiones.

### No genera el envío

Revisa:

- teléfono en cliente y almacén,
- código postal,
- estado/provincia,
- ciudad,
- peso y medidas,
- servicio ya sincronizado.

---

## 7. Recomendaciones

- Empieza siempre con **sandbox**.
- Haz una prueba completa con un pedido real de test.
- Si cambias el país de origen, el tipo de paquete o el entorno, vuelve a **sincronizar el servicio**.
- Revisa que el contacto del almacén tenga teléfono y dirección correctos.

---

## 8. Resumen rápido

Configuración mínima para que funcione:

1. Crear método de envío Envia.
2. Elegir entorno.
3. Pegar API key.
4. Seleccionar paquete por defecto.
5. Configurar país de origen.
6. Configurar moneda.
7. Elegir formato de etiqueta.
8. Sincronizar carrier/servicio.
9. Probar desde pedido de venta.

---

## 9. Archivos principales del módulo

- `__manifest__.py`
- `models/delivery_carrier.py`
- `models/envia_request.py`
- `models/stock_package_type.py`
- `views/delivery_carrier_views.xml`
- `wizard/envia_shipping_wizard.py`
- `wizard/envia_shipping_wizard.xml`

---

Si necesitas, el siguiente paso recomendable es documentar también una **checklist de validaciones de datos del cliente y del almacén** para evitar errores al crear el envío.

