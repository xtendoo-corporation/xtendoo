# Xtendoo WhatsApp POS Ticket

## Descripción

Este módulo permite enviar el ticket de venta del Punto de Venta (POS) de Odoo 18 por WhatsApp al cliente después de finalizar una venta.

## Características

- **Opción configurable**: En la configuración del POS, se puede activar o desactivar el envío de tickets por WhatsApp.
- **Selección de Gateway**: Permite seleccionar qué gateway de WhatsApp usar para el envío.
- **Plantillas personalizables**: Se pueden usar plantillas de WhatsApp configuradas para personalizar el mensaje.
- **Aviso de teléfono faltante**: Si el cliente seleccionado no tiene número de teléfono, se muestra un aviso.
- **Botón en pantalla de recibo**: Después del pago, aparece un botón para enviar el ticket por WhatsApp.
- **Envío de PDF**: El ticket se envía como archivo PDF adjunto.

## Dependencias

- `point_of_sale`: Módulo base del Punto de Venta de Odoo
- `mail_gateway_whatsapp`: Módulo OCA para gateway de WhatsApp
- `mail_gateway_whatsapp_variables`: Módulo Xtendoo para variables en plantillas de WhatsApp

## Configuración

1. Ir a **Punto de Venta > Configuración > Punto de Venta**
2. Seleccionar el POS a configurar
3. Ir a la pestaña **WhatsApp**
4. Activar **Habilitar envío de ticket por WhatsApp**
5. Seleccionar el **Gateway de WhatsApp** a utilizar
6. Opcionalmente, seleccionar una **Plantilla de WhatsApp** para personalizar el mensaje

## Uso

1. Realizar una venta en el POS
2. Seleccionar un cliente que tenga número de teléfono configurado
3. Completar el pago
4. En la pantalla de recibo, aparecerá el botón **Enviar por WhatsApp**
5. Hacer clic en el botón para enviar el ticket

## Notas

- El cliente debe tener un número de teléfono móvil o fijo configurado
- El número de teléfono debe incluir el código de país para funcionar correctamente con WhatsApp
- Se recomienda usar el campo "Móvil" para el número de WhatsApp

## Licencia

AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

## Autor

Xtendoo - https://www.xtendoo.es

