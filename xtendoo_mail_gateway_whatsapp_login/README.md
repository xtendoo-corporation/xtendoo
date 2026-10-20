# Xtendoo WhatsApp Embedded Login

Addon para Odoo 18 que añade un flujo de **Meta Embedded Signup** sobre el gateway de `mail_gateway_whatsapp`.

## Qué hace

- Añade un botón **Vincular con Meta** en `mail.gateway` cuando el tipo es WhatsApp.
- Abre el popup oficial del SDK de Meta.
- Intercambia el `code` devuelto por Meta por un token en backend.
- Intenta recuperar y mapear automáticamente:
  - `Meta Business ID`
  - `Meta WABA ID`
  - `Meta Phone Number ID`
  - `token`
  - `whatsapp_account_id`
  - `whatsapp_from_phone`

## Campos añadidos

- `xtendoo_meta_app_id`
- `xtendoo_meta_config_id`
- `xtendoo_meta_app_secret`
- `xtendoo_meta_business_id`
- `xtendoo_meta_waba_id`
- `xtendoo_meta_phone_number_id`
- `xtendoo_meta_phone_number`
- `xtendoo_meta_signup_state`
- `xtendoo_meta_last_response`
- `xtendoo_meta_last_error`

## Nota importante

Para poder intercambiar el `code` por un token en servidor, el addon necesita también el **Meta App Secret**. Por eso se añadió ese campo además de los dos que venían en la propuesta inicial.

## Limitación actual

Meta puede devolver estructuras distintas según la configuración del embedded signup y los permisos concedidos. El addon implementa una extracción robusta de los IDs más habituales, pero conviene validar el payload real en vuestro entorno de pruebas.

