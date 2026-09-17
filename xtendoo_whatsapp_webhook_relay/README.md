# Xtendoo WhatsApp Webhook Relay

## 1. Por qué existe este módulo

Meta solo permite **una única Callback URL por app** de WhatsApp. Como
`xtendoo_whatsapp_onboarding` conecta a muchos clientes bajo la misma app de
Xtendoo (cada uno con su propio dominio y su propia URL de webhook), Meta
solo puede entregar los mensajes entrantes a **una** URL — la que tenga
configurada Xtendoo. Este módulo recibe esos mensajes ahí, mira a qué
cliente pertenece cada uno (`phone_number_id` del payload) y se lo reenvía
a su Odoo, sin que Xtendoo tenga que procesarlos como si fueran suyos.

## 2. Dónde se instala

**Únicamente en el Odoo de producción de Xtendoo** (el que tiene registrada
la Callback URL real en el Meta App Dashboard). **Nunca en el Odoo de un
cliente** — ellos no necesitan ningún módulo nuevo para esto: el relé les
reenvía una petición POST normal a su webhook ya existente
(`mail_gateway`/`mail_gateway_whatsapp`, sin modificar), indistinguible de
si la hubiera llamado Meta directamente.

## 3. Cómo funciona

1. Meta llama a la Callback URL única de la app (p.ej.
   `https://xtdeoo.es/gateway/whatsapp/webhook4/update`), que resuelve al
   `mail.gateway` propio de Xtendoo.
2. Este módulo sobrescribe `mail.gateway.whatsapp._receive_update()`: por
   cada `change` del payload, mira `value.metadata.phone_number_id`.
   - Si coincide con el número propio de Xtendoo → se procesa exactamente
     igual que antes (comportamiento del OCA sin modificar).
   - Si es de un cliente **registrado** → se reenvía (POST) el payload
     filtrado (solo las entradas de ESE número, nunca las de otro cliente
     ni las de Xtendoo) a la URL de webhook del cliente, firmado con
     HMAC-SHA256 usando **el `webhook_secret` propio del cliente** — así su
     `_verify_update()`, sin modificar, lo acepta como si viniera de Meta.
   - Si no está registrado → se descarta y se registra en el log, nunca se
     procesa ni se reenvía a ningún sitio.
3. `xtendoo.whatsapp.relay.client` es el registro central
   `phone_number_id → URL de webhook + secreto` del cliente. Se rellena
   automáticamente: `xtendoo_whatsapp_onboarding` llama a
   `POST /xtendoo_whatsapp_relay/register` en cuanto un cliente completa el
   Embedded Signup, y a `POST /xtendoo_whatsapp_relay/unregister` cuando se
   desconecta. No requiere ningún paso manual por cliente.

## 4. Configuración necesaria

En **Ajustes → Ajustes generales → WhatsApp Webhook Relay (Xtendoo)**:

- **WhatsApp Relay API Key**: secreto compartido que deben enviar los
  clientes (header `X-Xtendoo-Relay-Key`) al registrarse/darse de baja.
  Debe coincidir exactamente con el que cada cliente configure en su propio
  `xtendoo_whatsapp_onboarding` (Relay API Key).

No hay más configuración: las URLs de los endpoints son fijas
(`/xtendoo_whatsapp_relay/register` y `/unregister`), y cada cliente ya
sabe su propia `webhook_url`/`webhook_secret` (los calcula él mismo al
registrarse, usando su propio `_get_webhook_url()`/`webhook_secret`).

## 5. Seguridad

- El API key nunca se hardcodea; vive en `ir.config_parameter`, como el
  resto de secretos de Xtendoo en estos módulos.
- Sin API key configurada, **todas** las peticiones se rechazan (403) — un
  relé sin configurar no acepta registros por error.
- `webhook_secret` de cada cliente se guarda para poder firmar los reenvíos,
  nunca se expone en logs ni en la respuesta de los endpoints.
- Un `phone_number_id` solo puede pertenecer a un cliente a la vez
  (restricción única en base de datos); volver a registrar el mismo número
  actualiza sus datos (útil si el cliente reconecta), no crea duplicados.
- Cada mensaje reenviado contiene **únicamente** las entradas de ESE
  cliente — nunca se reenvía o procesa localmente contenido de otro cliente
  aunque Meta los batchee en la misma llamada (cubierto por tests).

## 6. Cómo probarlo

Tests automáticos (mockeando las llamadas HTTP salientes, sin depender de
Meta real):

```bash
docker compose run --rm -e "DB_FILTER=^<db>$" odoo odoo --test-enable \
  --stop-after-init --workers=0 -d <db> -u xtendoo_whatsapp_webhook_relay \
  --test-tags /xtendoo_whatsapp_webhook_relay
```

`DB_FILTER` es necesario porque los tests del controlador (`HttpCase`)
hacen peticiones HTTP reales; sin fijar la base de datos objetivo, en un
Postgres con varias bases de datos Odoo no sabe a cuál dirigir la petición
y las rutas devuelven 404 aunque el código sea correcto.

## 7. Limitaciones actuales

- No hay reintento automático si el reenvío a un cliente falla (por
  ejemplo, su Odoo está caído en ese instante) — el mensaje se pierde para
  ese envío concreto; queda registrado en `last_relay_error` del cliente
  para poder investigarlo, pero Meta no reintenta indefinidamente sus
  propios webhooks tampoco.
- Si Xtendoo tiene más de un número propio, este módulo asume que todos los
  webhooks de la app llegan a través de un único `mail.gateway` propio (el
  resuelto por la URL registrada en Meta); no contempla varios gateways
  "propios" a la vez.
- No implementa un panel de monitorización; el estado de cada cliente
  registrado se revisa en el modelo `xtendoo.whatsapp.relay.client`
  (menú WhatsApp Relay Clients).
