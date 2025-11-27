# Mail Gateway WhatsApp - Template Variables

## Descripción

Este módulo extiende `mail_gateway_whatsapp` (OCA) para agregar soporte de variables dinámicas en las plantillas de WhatsApp, similar a la funcionalidad del módulo enterprise.

## Características

- ✅ Soporte para hasta 10 variables en plantillas ({{1}}, {{2}}, ..., {{10}})
- ✅ Detección automática de variables en plantillas
- ✅ Campos dinámicos que aparecen solo si la plantilla tiene variables
- ✅ Auto-población inteligente de variables desde el registro actual
- ✅ Reemplazo automático de placeholders antes de enviar
- ✅ Compatible con plantillas OCA existentes

## Dependencias

- `mail_gateway_whatsapp` (OCA)

## Instalación

1. Asegúrate de tener instalado `mail_gateway_whatsapp`
2. Instala este módulo desde Aplicaciones
3. Las variables se detectarán automáticamente en tus plantillas

## Uso

### Crear plantillas con variables

En tu plantilla de WhatsApp, usa placeholders con números entre llaves dobles:

```
Hola {{1}},

Tu pedido {{2}} por un monto de {{3}} ha sido confirmado.

Fecha de entrega: {{4}}

Gracias por tu compra!
```

### Enviar mensaje con variables

1. Abre cualquier registro (contacto, venta, factura, etc.)
2. Haz clic en el botón "WhatsApp" en el chatter
3. Selecciona una plantilla con variables
4. **Los campos de variables aparecerán automáticamente**
5. El módulo intentará llenarlos automáticamente desde el registro
6. Revisa y ajusta los valores si es necesario
7. Envía el mensaje

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

## Troubleshooting

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

