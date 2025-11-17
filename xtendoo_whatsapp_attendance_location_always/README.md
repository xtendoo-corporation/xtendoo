# Xtendoo WhatsApp Attendance - Location Always

## Descripción

Este módulo es una variante del módulo base `xtendoo_whatsapp_attendance` que **siempre solicita la ubicación del empleado** sin preguntar previamente.

## Diferencia Principal

### Módulo Base (xtendoo_whatsapp_attendance)
- ❓ Pregunta al usuario: "¿Deseas compartir tu ubicación?"
- 🔘 Muestra dos botones: "Con ubicación" / "Sin ubicación"
- 👤 El usuario decide si compartir o no su ubicación

### Este Módulo (xtendoo_whatsapp_attendance_location_ever)
- 📍 **Solicita DIRECTAMENTE la ubicación**
- 📝 Envía instrucciones claras de cómo compartir ubicación
- ⏰ Espera 3 minutos a que el usuario envíe su ubicación
- ✅ Registra la asistencia solo cuando recibe la ubicación

## Características

✅ Registro automático de entradas y salidas mediante comandos de WhatsApp
✅ **Solicitud directa de ubicación (sin pregunta previa)**
✅ Palabras clave personalizables para entrada y salida
✅ Plantillas de respuesta configurables
✅ Geolocalización siempre solicitada para empleados con tracking activado
✅ Webhook personalizado para integración con WhatsApp Business API

## Flujo de Trabajo

1. **Empleado envía comando** (ejemplo: "entrada" o "/checkin")
2. **Sistema valida** el comando y busca al empleado
3. **Si tiene geolocalización activada:**
   - ✅ Envía mensaje con instrucciones para compartir ubicación
   - ⏰ Espera a que el empleado envíe su ubicación
   - 📍 Registra asistencia con la ubicación recibida
4. **Si NO tiene geolocalización activada:**
   - ✅ Registra asistencia sin ubicación

## Instalación

1. Copiar el módulo a la carpeta de addons personalizados
2. Actualizar lista de módulos en Odoo
3. Instalar el módulo desde Apps

## Configuración

### Habilitar Geolocalización por Empleado

1. Ir a **Empleados**
2. Abrir el empleado deseado
3. En la pestaña **Settings** → sección **Attendance/Point of Sale**
4. Activar el campo **WhatsApp Geolocation**

### Configurar Palabras Clave

El módulo usa las mismas configuraciones de palabras clave que el módulo base.

## Dependencias

- base
- whatsapp
- hr
- hr_attendance

## Versión

- **Odoo:** 19.0
- **Versión del módulo:** 1.0.0

## Autor

**Xtendoo**
- Website: https://www.xtendoo.com

## Licencia

LGPL-3

## Notas Técnicas

### Modificaciones Respecto al Módulo Base

1. **Método `_request_location_for_attendance`:**
   - Modificado para llamar a `_send_direct_location_request` en lugar de `_send_location_request_with_button`

2. **Nuevo Método `_send_direct_location_request`:**
   - Envía mensaje de texto simple con instrucciones claras
   - No usa botones interactivos

3. **Procesamiento de Mensajes:**
   - Eliminado el procesamiento de botones interactivos
   - Espera directamente la respuesta con ubicación

## Comparación Visual

### Módulo Base
```
Usuario: entrada
Bot: ¿Deseas compartir ubicación?
     [📍 Con ubicación] [✅ Sin ubicación]
Usuario: [presiona botón]
Bot: [procesa según elección]
```

### Este Módulo
```
Usuario: entrada
Bot: Para registrar tu entrada, comparte tu ubicación:
     1️⃣ Toca 📎
     2️⃣ Selecciona Ubicación
     3️⃣ Elige Ubicación actual
     4️⃣ Envía
Usuario: [envía ubicación]
Bot: ✅ Entrada registrada con ubicación
```

## Soporte

Para soporte técnico, contactar a Xtendoo.

