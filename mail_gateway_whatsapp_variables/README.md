# Mail Gateway WhatsApp - Template Variables

## Descripción

Este módulo extiende `mail_gateway_whatsapp` (OCA) para agregar soporte de variables dinámicas, botones y **adjuntos automáticos** en las plantillas de WhatsApp.

## Características

- ✅ Soporte para hasta 10 variables en plantillas ({{1}}, {{2}}, ..., {{10}})
- ✅ Detección automática de variables en plantillas
- ✅ Campos dinámicos que aparecen solo si la plantilla tiene variables
- ✅ Auto-población inteligente de variables desde el registro actual
- ✅ Reemplazo automático de placeholders antes de enviar
- ✅ **Generación automática de PDFs** para ventas y facturas 📄
- ✅ **Auto-adjuntar PDFs** al abrir el composer desde ventas/facturas
- ✅ Soporte de adjuntos múltiples (PDFs, imágenes, documentos)
- ✅ Botones interactivos (quick_reply, URL, llamada)
- ✅ **Plantillas predefinidas** para ventas, albaranes y facturas 🎯
- ✅ **Wizard de importación** de plantillas con un clic
- ✅ Compatible con plantillas OCA existentes

## Versión

**18.0.1.8.0** - Plantillas predefinidas implementadas

### Cambios en v1.8.0 (7 Enero 2026)
- ✨ **NUEVO**: 6 plantillas predefinidas listas para usar
- ✨ **NUEVO**: Wizard de importación de plantillas
- ✨ **NUEVO**: Menú de WhatsApp en Discuss
- ✨ **NUEVO**: Plantillas con y sin botones interactivos
- 📝 Plantillas para: Pedidos, Albaranes y Facturas

### Cambios en v1.7.0 (2 Enero 2026)
- ✨ **NUEVO**: Generación automática de PDFs al abrir composer
- ✨ **NUEVO**: Auto-adjuntar PDF de presupuesto/pedido desde ventas
- ✨ **NUEVO**: Auto-adjuntar PDF de factura desde facturas
- 🔧 Los PDFs se generan automáticamente al hacer clic en "WhatsApp"
- 📝 El usuario puede quitar o añadir más archivos antes de enviar

## Dependencias

- `mail_gateway_whatsapp` (OCA)
- `sale` (para auto-generación de PDFs de ventas)
- `account` (para auto-generación de PDFs de facturas)

## Instalación

1. Asegúrate de tener instalado `mail_gateway_whatsapp`
2. Instala este módulo desde Aplicaciones
3. Las variables se detectarán automáticamente en tus plantillas

## Uso

### 🎯 Importar Plantillas Predefinidas (NUEVO)

El módulo incluye 6 plantillas listas para usar:

1. Ve a **Discuss → WhatsApp → Obtener Plantillas del Módulo**
2. Selecciona tu **Gateway de WhatsApp**
3. Marca las plantillas que deseas importar:
   - ✅ Confirmación de Pedido (sin botones)
   - ✅ ¿Quiere recibir PDF del Pedido? (con botones)
   - ✅ Notificación de Envío (sin botones)
   - ✅ ¿Quiere recibir PDF del Albarán? (con botones)
   - ✅ Factura Disponible (sin botones)
   - ✅ ¿Quiere recibir PDF de la Factura? (con botones)
4. Haz clic en **"Importar Plantillas"**
5. ¡Listo! Las plantillas aparecerán en tu lista de plantillas

**Plantillas con botones interactivos:** Incluyen footer "Responda Sí o No" para que el cliente pueda confirmar si desea recibir el PDF del documento.

### Enviar mensaje con PDF desde Venta

1. Abre un **Presupuesto** o **Pedido de Venta**
2. Haz clic en el botón **"WhatsApp"** en el chatter
3. **El PDF se genera y adjunta automáticamente** ✨
4. Selecciona una plantilla con variables
5. Las variables se llenan automáticamente
6. Puedes quitar el PDF o añadir más archivos
7. Envía el mensaje

### Enviar mensaje con PDF desde Factura

1. Abre una **Factura de Cliente**
2. Haz clic en el botón **"WhatsApp"** en el chatter
3. **El PDF de la factura se genera y adjunta automáticamente** ✨
4. Selecciona una plantilla
5. Envía el mensaje

### Crear plantillas con variables

En tu plantilla de WhatsApp, usa placeholders con números entre llaves dobles:

```
Hola {{1}},

Tu pedido {{2}} por un monto de {{3}} ha sido confirmado.

Fecha de entrega: {{4}}

Gracias por tu compra!
```

### Comportamiento de PDFs Automáticos

El módulo genera automáticamente PDFs para:

| Modelo | PDF Generado | Nombre del Archivo |
|--------|--------------|-------------------|
| **sale.order** (borrador) | Presupuesto | `Quotation_S00001.pdf` |
| **sale.order** (confirmado) | Pedido de Venta | `Order_SO001.pdf` |
| **account.move** (factura) | Factura | `Invoice_INV/2024/0001.pdf` |
| **account.move** (nota crédito) | Nota de Crédito | `Refund_RINV/2024/0001.pdf` |

### Variables automáticas por modelo

El módulo intenta llenar variables automáticamente según el modelo:

**res.partner (Contactos):**
- {{1}} → Nombre
- {{2}} → Email
- {{3}} → Teléfono
- {{4}} → Móvil
- {{5}} → Dirección
- {{6}} → Ciudad

**sale.order (Ventas):**
- {{1}} → Nombre del cliente
- {{2}} → Número de pedido
- {{3}} → Total
- {{4}} → Fecha

**account.move (Facturas):**
- {{1}} → Nombre del cliente
- {{2}} → Número de factura
- {{3}} → Total
- {{4}} → Fecha de factura

## Formato de variables en plantillas

### Sintaxis correcta:
- `{{1}}`, `{{2}}`, `{{3}}`, etc.
- Números del 1 al 10
- Llaves dobles `{{` y `}}`

### NO válido:
- `{1}` (una sola llave)
- `{{ 1 }}` (espacios dentro)
- `{{nombre}}` (texto en lugar de número)

## Compatibilidad

- Odoo 18.0
- Compatible con `mail_gateway_whatsapp` (OCA)
- Compatible con `mail_gateway_whatsapp_chatter`

## Ejemplos de plantillas

### Template 1: Confirmación de pedido
```
Hola {{1}},

Tu pedido {{2}} ha sido confirmado.
Total: ${{3}}
Fecha de entrega estimada: {{4}}

Gracias por tu compra!
```

### Template 2: Recordatorio de cita
```
Estimado/a {{1}},

Le recordamos su cita para el {{2}} a las {{3}}.
Lugar: {{4}}

Por favor confirme su asistencia.
```

### Template 3: Estado de envío
```
Hola {{1}},

Tu paquete {{2}} está en camino.
Código de seguimiento: {{3}}
Llegada estimada: {{4}}
```

## Configuración avanzada

### Agregar mapeos personalizados

Puedes extender el método `_populate_variables_from_record()` para agregar mapeos para tus modelos custom:

```python
def _populate_variables_from_record(self):
    super()._populate_variables_from_record()

    if self.res_model == 'mi.modelo.custom':
        record = self.env[self.res_model].browse(self.res_id)
        self.variable_1 = record.campo1
        self.variable_2 = record.campo2
        # ... etc
```

## ⚠️ Importante: Limitación de WhatsApp con Adjuntos

### Regla de las 24 Horas

WhatsApp Business API tiene una restricción importante:

**Los adjuntos (PDFs, imágenes, etc.) solo se entregan si estás dentro de la ventana de 24 horas desde el último mensaje del cliente.**

#### Cómo funciona:

```
Cliente te envía mensaje → Se abre ventana de 24h
   ↓
Dentro de 24h: Puedes enviar plantillas + PDFs ✅
   ↓
Después de 24h: Solo puedes enviar plantillas (sin PDFs) ❌
```

#### Escenarios:

| Situación | Plantilla | PDF | Resultado |
|-----------|-----------|-----|-----------|
| Cliente escribió hace 10 horas | ✅ Se envía | ✅ Se envía | ✅ Ambos llegan |
| Cliente escribió hace 3 días | ✅ Se envía | ❌ Se descarta | ⚠️ Solo plantilla llega |
| Primera vez (sin conversación) | ✅ Se envía | ❌ Se descarta | ⚠️ Solo plantilla llega |

#### Solución Recomendada:

Para **nuevos clientes** sin conversación reciente:
1. Envía la plantilla primero (sin PDF)
2. Espera a que el cliente responda
3. **Ahora** envía el PDF (estarás en ventana de 24h)

Para **clientes activos** (< 24h):
- ✅ Envía plantilla + PDF juntos
- Todo funcionará correctamente

#### Notas Técnicas:

- El código **SÍ envía el PDF** (verás status 200 OK en logs)
- WhatsApp **acepta** el mensaje
- Pero lo **descarta silenciosamente** si estás fuera de 24h
- Esta es una **limitación de WhatsApp Business API**, no del módulo

## Troubleshooting

### El PDF no llega al cliente

**Causa más probable**: Estás fuera de la ventana de 24 horas.

**Solución**:
1. Verifica cuándo fue el último mensaje del cliente
2. Si fue hace más de 24h:
   - Envía solo la plantilla (quita el PDF)
   - Espera respuesta del cliente
   - Luego envía el PDF
3. Si fue hace menos de 24h y aún no llega:
   - Verifica que el cliente tenga WhatsApp
   - Confirma el número de teléfono
   - Revisa los logs de Odoo para errores

### Las variables no se reemplazan

- Verifica que uses la sintaxis correcta: `{{1}}`, `{{2}}`, etc.
- Asegúrate de que los números estén entre 1 y 10
- Confirma que has llenado todos los campos de variables requeridos

### Los campos de variables no aparecen

- Verifica que la plantilla contenga placeholders `{{número}}`
- Asegúrate de haber seleccionado una plantilla
- Revisa que el módulo esté instalado correctamente

## Créditos

### Autores

- Xtendoo

### Contribuidores

- Manuel Calero

## Licencia

AGPL-3

## Soporte

Para soporte, contacta con Xtendoo o abre un issue en GitHub.

