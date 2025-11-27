# Mail Gateway WhatsApp - Chatter Integration

## Descripción

Este módulo extiende `mail_gateway_whatsapp` (OCA) para agregar un botón de WhatsApp en el chatter de Odoo, similar a la funcionalidad del módulo enterprise de WhatsApp.

## Características

- ✅ Botón "WhatsApp" en el chatter de todos los registros con teléfono
- ✅ Integración automática con el wizard `whatsapp.composer` existente
- ✅ Detección automática de gateways de WhatsApp configurados
- ✅ Respeta la lógica de ventana de 24h para requerir plantillas
- ✅ Contador de conversaciones de WhatsApp en contactos
- ✅ Botón estadístico para acceder a conversaciones desde el contacto

## Dependencias

- `mail_gateway_whatsapp` (OCA)
- `web`

## Instalación

1. Asegúrate de tener instalado `mail_gateway_whatsapp`
2. Instala este módulo desde Aplicaciones
3. Configura al menos un gateway de WhatsApp en Configuración → Técnico → Mail Gateway

## Uso

### Enviar mensaje desde el chatter

1. Abre cualquier registro que tenga campo de teléfono (ej: contacto, venta, factura)
2. En el chatter, verás un botón "WhatsApp" (con el icono verde)
3. Haz clic en el botón para abrir el composer
4. El wizard detectará automáticamente:
   - Si necesitas usar una plantilla (ventana de 24h)
   - El campo de teléfono correcto
   - El gateway configurado

### Ver conversaciones desde contacto

En la vista de contacto (res.partner), verás un botón estadístico que muestra:
- Número de conversaciones de WhatsApp activas
- Al hacer clic, accedes a la lista de todas las conversaciones

## Configuración

### Campo de teléfono

El módulo detecta automáticamente el campo de teléfono basándose en:
1. Modelos que heredan `mail.thread.phone`
2. Campos comunes: `mobile`, `phone`, `partner_id.mobile`, `partner_id.phone`

### Lógica de plantillas (24h)

- Si la última conversación fue hace **menos de 24 horas**: puedes enviar texto libre
- Si la última conversación fue hace **más de 24 horas**: debes usar una plantilla aprobada

Esta lógica es gestionada automáticamente por el wizard `whatsapp.composer` del módulo base.

## Teclas rápidas

- `Shift + W`: Abrir composer de WhatsApp (cuando el botón está visible)

## Compatibilidad

- Odoo 18.0
- Compatible con la arquitectura `mail.gateway`
- Funciona con cualquier proveedor de WhatsApp Business API

## Créditos

### Autores

- Xtendoo

### Contribuidores

- Manuel Calero

## Licencia

AGPL-3

## Soporte

Para soporte, contacta con Xtendoo o abre un issue en GitHub.

