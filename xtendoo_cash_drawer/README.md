# Xtendoo Cash Drawer

Módulo Odoo 19 para controlar el cajón portamonedas desde el TPV mediante un **bridge local**.

La apertura del cajón se realiza **directamente desde el navegador del TPV** al bridge local
instalado en el PC del cajero o en la LAN del cliente. Odoo no actúa como proxy: no se
realizan peticiones Python al cajón.

---

## Arquitectura

```
Navegador del TPV (Chrome/Firefox)
         │
         │  GET /open-drawer?printer=POS-80C
         │  Header: x-api-key: <tu_clave>
         ▼
Bridge local (Windows/Linux, PC del cajero)
http://127.0.0.1:3211   ←── por defecto
         │
         ▼
Cajón portamonedas (puerto serie/USB)
```

> **¿Por qué no el proxy de Odoo?**
> Odoo puede estar en la nube o en Docker. Desde el servidor Odoo es imposible
> alcanzar `127.0.0.1` del PC del cajero. El bridge local resuelve ese problema:
> el navegador del cajero sí puede llegar a su propio `127.0.0.1`.

---

## Requisitos

| Componente | Requisito |
|---|---|
| Odoo | 19.0 |
| Módulo base | `point_of_sale` |
| Bridge | Cualquier bridge HTTP local que exponga `/open-drawer` y `/health` |
| CORS | El bridge **debe** devolver cabeceras CORS (ver sección CORS) |

---

## Instalación

1. Copia el módulo a la carpeta de addons de Odoo.
2. Actualiza la lista de módulos: **Ajustes → Activar modo desarrollador → Actualizar lista de módulos**.
3. Instala **Xtendoo Cash Drawer** desde la lista de módulos.

---

## Configuración

Los ajustes están disponibles en dos lugares equivalentes:

### Opción A — TPV individual

`Punto de Venta → Configuración → TPV → (abre el TPV) → sección "Cajón portamonedas"`

### Opción B — Ajustes generales del POS

`Ajustes → Punto de Venta → sección "Cajón portamonedas (bridge local)"`

### Campos disponibles

| Campo | Descripción | Valor por defecto |
|---|---|---|
| **Usar bridge local** | Activa la integración con el bridge | `false` |
| **URL del bridge local** | URL base del bridge en el PC del cajero | `http://127.0.0.1:3211` |
| **Nombre de la impresora** | Se envía al bridge como `?printer=<nombre>` | *(vacío)* |
| **API Key del bridge** | Cabecera `x-api-key` enviada al bridge | *(vacío)* |
| **Apertura automática en efectivo** | Abre el cajón al validar un pago en efectivo | `true` |

> **Campo legado:** Si venías de una versión anterior con `URL de apertura del cajón (legado)`,
> ese campo se conserva para compatibilidad. El módulo lo usará como fallback si
> `URL del bridge local` está vacía. Se recomienda migrar al nuevo campo.

### Pasos de configuración básica

1. Activa **Usar bridge local** ✓
2. Comprueba la **URL del bridge local** (por defecto `http://127.0.0.1:3211`)
   — cámbiala a la IP del PC del cajero si es diferente, p. ej. `http://192.168.1.50:3211`
3. Introduce el **Nombre de la impresora** tal como lo reconoce el bridge, p. ej. `POS-80C`
4. Si el bridge requiere autenticación, rellena la **API Key del bridge**
5. Decide si quieres **apertura automática en pagos en efectivo**
6. Haz clic en **Guardar**
7. Pulsa **Probar apertura del cajón** para verificar que todo funciona

---

## Probar la conexión

Desde la configuración del TPV o desde Ajustes, el botón **"Probar apertura del cajón"**
abre un diálogo que:

- Muestra la URL de apertura que se usará (`/open-drawer?printer=...`)
- Muestra la URL de health check (`/health`)
- Permite **verificar el bridge** (GET `/health`) antes de abrir
- Permite **abrir el cajón** (GET `/open-drawer?printer=...`) como prueba

La prueba se ejecuta **desde el navegador del usuario**, no desde Python, por lo que
valida exactamente el mismo canal de red que usará el cajero en el TPV.

---

## Uso en el TPV

### Botón manual

Cuando el bridge está habilitado y configurado, aparece un botón 🔓 **"Abrir Cajón"**:

- En el área de botones de control de la pantalla de productos
- En la barra de navegación superior del TPV

Pulsa cualquiera de ellos para abrir el cajón manualmente.

### Apertura automática

Si **Apertura automática en efectivo** está activo, el cajón se abrirá solo al
validar un pedido que contenga algún pago con método de tipo **efectivo**
(`is_cash_count = true`).

Si el bridge falla, se muestra un aviso pero **el cobro se completa igualmente**.
La sesión del TPV nunca queda en estado inconsistente por un fallo del cajón.

---

## API esperada del bridge

El bridge local debe implementar los siguientes endpoints:

### `GET /open-drawer`

Abre el cajón portamonedas.

```
GET /open-drawer?printer=POS-80C
x-api-key: tu_clave_api
```

Respuesta esperada:

```json
{ "ok": true }
```

En caso de error:

```json
{ "ok": false, "error": "Descripción del error" }
```

### `GET /health`

Comprueba que el bridge está en ejecución.

```
GET /health
```

Respuesta esperada:

```json
{ "status": "ok" }
```

---

## CORS

El bridge recibe peticiones desde la web de Odoo (origen distinto), por lo que
**debe devolver cabeceras CORS** en todas las respuestas, incluidas las preflight (`OPTIONS`):

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Headers: x-api-key, Content-Type
Access-Control-Allow-Methods: GET, OPTIONS
```

Si el bridge no tiene CORS configurado, el navegador bloqueará la respuesta y
el módulo mostrará un error de red. El bridge debe actualizarse en ese caso.

---

## Compatibilidad con versiones anteriores

| Escenario | Comportamiento |
|---|---|
| `cash_drawer_use_bridge = false` y `cash_drawer_open_url` relleno | El JS del POS usa el valor legacy como fallback. La funcionalidad se mantiene. |
| `cash_drawer_use_bridge = true` y `cash_drawer_bridge_url` relleno | Usa la nueva arquitectura. Recomendado. |
| Ambos campos rellenos | Tiene prioridad `cash_drawer_bridge_url`. |
| Ningún campo relleno | El botón no aparece en el TPV. |

Para migrar desde la versión anterior:

1. Copia el valor de `URL de apertura del cajón (legado)` a `URL del bridge local`
   (elimina el path `/open-drawer?...` si lo incluía, deja solo la base: `http://IP:PUERTO`)
2. Rellena `Nombre de la impresora` con el valor que tenías en el query param `?printer=`
3. Activa **Usar bridge local**
4. Vacía el campo legado (opcional, pero recomendado para mantener el módulo limpio)

---

## Autor

- **Empresa**: Xtendoo
- **Web**: https://xtendoo.es
- **Licencia**: LGPL-3

