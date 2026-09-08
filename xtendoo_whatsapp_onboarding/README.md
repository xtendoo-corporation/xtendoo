# Xtendoo WhatsApp Onboarding

## 1. Objetivo

Permitir que una empresa cliente conecte su propia cuenta de WhatsApp
Business a Odoo mediante el flujo oficial de Meta **WhatsApp Embedded
Signup** (Facebook Login for Business), sin tener que entrar en Meta
Developers, crear una app propia, copiar tokens/IDs ni configurar webhooks a
mano.

Esta primera fase cubre **exclusivamente el alta de nuevas conexiones**:

```
ODOO → META EMBEDDED SIGNUP → AUTORIZACIÓN DEL CLIENTE → WABA DEL CLIENTE
     → PHONE NUMBER DEL CLIENTE → CONFIGURACIÓN EN ODOO
```

No implementa envío/recepción de mensajes, conversaciones, plantillas ni
campañas: esa funcionalidad ya existe en `mail_gateway_whatsapp` y módulos
relacionados, y este módulo se limita a dejar el `mail.gateway`
correctamente configurado para que la usen.

No cubre el escenario de "coexistencia" (migrar un número que ya está
activo en la app móvil WhatsApp Business App): eso es un flujo distinto de
Meta (con verificación OTP/QR) fuera del alcance de esta fase.

## 2. Instalación

1. Asegúrate de que `mail_gateway_whatsapp` (OCA) está instalado.
2. Instala `xtendoo_whatsapp_onboarding`.
3. Ve a **Ajustes → Ajustes generales** y rellena el bloque **"WhatsApp
   Embedded Signup (Xtendoo)"** (ver sección 6). Solo lo puede editar un
   usuario con el grupo *Ajustes/Técnico* (`base.group_system`).

## 3. Dependencias

- `mail_gateway_whatsapp`: dependencia técnica real. Este módulo escribe
  directamente sobre `whatsapp_account_id`, `whatsapp_from_phone` y usa el
  motor de envío/recepción y el webhook ya existentes.
- `web`: para el asset JS del SDK de Meta y la acción de cliente.

**Deliberadamente NO son dependencias del manifest** (aunque deben estar
instalados en el entorno de pruebas): `mail_gateway_whatsapp_chatter`,
`mail_gateway_whatsapp_variables`, `xtendoo_booking_reserve_whatsapp`. Son
módulos de UI/negocio de mensajería que no participan en el onboarding; no
se les llama desde ningún punto de este módulo.

## 4. Configuración en Odoo

El modelo de conexión es el `mail.gateway` ya existente (no se crea un
modelo nuevo): se reutiliza y se le añaden campos de estado/auditoría con
prefijo `whatsapp_onboarding_*`.

Pantalla: **Ajustes → Técnico → Correo → WhatsApp** (o el formulario del
gateway, pestaña "WhatsApp" si ya existe). Ahí aparece:

- Estado (`draft` / `connecting` / `connected` / `error` / `disconnected`)
  como barra de progreso.
- Botón **Connect WhatsApp** (visible si no está conectado).
- Botón **Resync** y **Disconnect** (visibles si está conectado).
- Datos de solo lectura tras conectar: WABA ID, Phone Number ID, número de
  teléfono visible, Business Portfolio ID, fecha de conexión, última
  sincronización.
- Mensaje de error técnico si el estado es `error`.

## 5. Configuración necesaria en Meta

Estos valores pertenecen a **Xtendoo** (no al cliente) y se configuran una
única vez en **Ajustes → Ajustes generales → WhatsApp Embedded Signup
(Xtendoo)**:

### 6. App ID
Meta App ID de la app de Xtendoo (`ir.config_parameter`:
`xtendoo_whatsapp_onboarding.meta_app_id`).

### 7. App Secret
Meta App Secret de la app de Xtendoo (`xtendoo_whatsapp_onboarding.meta_app_secret`).
Se usa **solo en el servidor** para intercambiar el `code` de autorización
por un token (`GET /oauth/access_token`). Nunca se envía al navegador, no
se registra en logs y el campo se muestra como contraseña en la UI.

### 8. Embedded Signup Configuration ID
ID de la configuración de "Facebook Login for Business" usada para el
Embedded Signup (`xtendoo_whatsapp_onboarding.meta_config_id`). Se obtiene
en el Meta App Dashboard → Facebook Login for Business → Configurations.
Vuestra app ya tiene una plantilla creada ("...con token de caducidad de 60
días"): **verificar antes de producción** si genera un token que caduca a
los 60 días o no (ver sección 18, limitación conocida).

### 9. Redirect URLs / Dominios
El dominio desde el que se abre el popup de Odoo debe estar dado de alta en
esa Configuration, en **Allowed Domains** y **Valid OAuth Redirect URIs**
del producto Facebook Login for Business.

### 10. Webhooks
El **Callback URL es único a nivel de app** (no por cliente), se configura
una sola vez en el Meta App Dashboard apuntando al endpoint ya existente en
`mail_gateway` (`<url-base>/gateway/whatsapp/<webhook_key>/update`). El
onboarding, por cada cliente, hace `POST /{waba_id}/subscribed_apps` para
que los eventos de esa WABA lleguen a ese callback. Sin ese paso (que este
módulo sí automatiza) los mensajes de un cliente conectado no llegarían al
webhook aunque el signup se complete correctamente.

### 11. Permisos
`whatsapp_business_management`, `whatsapp_business_messaging` en la
Configuration del Embedded Signup. **Pendiente de verificar manualmente**:
que ambos permisos estén en *Advanced Access* (no solo *Standard*) en el
Dashboard de Meta — es un requisito de Meta para operar sobre WABAs de
terceros como Tech Provider, y no es derivable desde el código.

## 12. Flujo de onboarding

```
Usuario pulsa "Connect WhatsApp"
  → Odoo (backend) valida configuración Xtendoo y genera un "session" único
  → Frontend: FB.init + FB.login(config_id) [SDK oficial de Meta]
  → Meta: login, selección/creación de negocio, WABA y número, autorización
  → Frontend recibe (1) postMessage WA_EMBEDDED_SIGNUP con waba_id/
    phone_number_id/business_id y (2) un "code" de un solo uso (caduca en
    30 segundos)
  → Frontend envía code + session + IDs al backend Odoo (RPC)
  → Backend Odoo intercambia el code por un token vía
    GET https://graph.facebook.com/v<version>/oauth/access_token
    (server-to-server, con el App Secret de Xtendoo)
  → Backend Odoo hace POST /{waba_id}/subscribed_apps con el token
    (necesario para que lleguen los webhooks de esa WABA)
  → Backend Odoo guarda: token, whatsapp_account_id, whatsapp_from_phone,
    business_id, número visible, y marca el gateway como "connected"
  → UI: 🟢 WhatsApp conectado
```

## 13. Qué tiene que hacer el cliente

Solo: pulsar "Connect WhatsApp", iniciar sesión en Meta, seleccionar/crear
su negocio, WABA y número, y aceptar los permisos solicitados. Nada técnico.

## 14. Qué hace automáticamente Odoo

Genera el `session` de idempotencia, intercambia el `code` por un token,
resuelve WABA/Phone Number ID, evita duplicados (una WABA/número no puede
quedar conectada a dos gateways a la vez), suscribe la app al WABA
(`subscribed_apps`), guarda las credenciales en el `mail.gateway` existente
y actualiza el estado visible.

## 15. Qué datos devuelve Meta

Del `postMessage WA_EMBEDDED_SIGNUP`: `waba_id`, `phone_number_id`,
`business_id` (más `event`: `FINISH` o `CANCEL`). Del intercambio del
`code`: un `access_token` (Business Integration System User token, scoped
al cliente). De `GET /{phone_number_id}`: `display_phone_number` y
`verified_name`.

## 16. Cómo probarlo

1. Instalar `mail_gateway_whatsapp`, `mail_gateway_whatsapp_chatter`,
   `mail_gateway_whatsapp_variables`, `xtendoo_booking_reserve_whatsapp` y
   `xtendoo_whatsapp_onboarding`.
2. Rellenar App ID / App Secret / Config ID de Xtendoo en Ajustes generales.
3. Crear o abrir un `mail.gateway` de tipo WhatsApp y pulsar "Connect
   WhatsApp".
4. Completar el flujo de Meta con una cuenta de prueba.
5. Verificar que el gateway queda en estado "Connected" con WABA ID, Phone
   Number ID y número visibles, y que `button_import_whatsapp_template()`
   (de `mail_gateway_whatsapp`) funciona con el token obtenido.
6. Tests automáticos (sin cuenta Meta real, HTTP mockeado):
   `odoo-bin -d <db> -i xtendoo_whatsapp_onboarding --test-enable
   --test-tags xtendoo_whatsapp_onboarding --stop-after-init`

## 17. Limitaciones actuales

- **Duración real del token no verificada empíricamente.** La
  Configuration de Meta usada actualmente se llama "...con token de
  caducidad de 60 días". No hay evidencia real (ver
  `FASE0_EVIDENCIAS_META.md` en la raíz del proyecto, aún sin rellenar) de
  si el token BISU final caduca a los 60 días o no. Hasta confirmarlo con
  `GET /debug_token`, este módulo **no implementa renovación automática de
  token** — si caduca, el estado pasará a `error` en el primer `Resync` o
  envío fallido y habrá que repetir el Embedded Signup.
- **Advanced Access no verificado.** No se puede confirmar desde código si
  `whatsapp_business_management`/`whatsapp_business_messaging` están en
  Advanced Access en el Dashboard de Meta; es un requisito de Meta para
  Tech Providers que opera sobre WABAs de clientes.
- La verificación de que el `access_token` obtenido realmente tiene permiso
  sobre el `waba_id`/`phone_number_id` indicados por el frontend se delega
  por completo en las respuestas de error de la propia Graph API (si no
  coincide, `subscribed_apps` o la consulta del número fallarán) — no se
  hace una comprobación explícita adicional (p. ej. `debug_token`).
- No hay wizard de configuración inicial: los parámetros de Xtendoo se
  configuran vía Ajustes generales.

## 18. Qué queda pendiente para la siguiente fase

- Confirmar duración real del token y, si caduca, implementar el mecanismo
  de renovación correcto (Fase 4 del plan original).
- Verificar Advanced Access y Business Verification de la app de Xtendoo.
- Mensajería, conversaciones, plantillas, campañas: fuera de alcance,
  ya cubiertas por `mail_gateway_whatsapp` y módulos relacionados.
- Posible menú/asistente de configuración más guiado para el cliente final.
- Rellenar `FASE0_EVIDENCIAS_META.md` con una prueba real contra la app de
  Meta de Xtendoo antes de pasar a producción con clientes reales.
