# xtd_pos_serial_scale - Balanza Serie para POS (Web Serial API)

## Descripción

Módulo para Odoo 19 que permite conectar una balanza electrónica al Punto de Venta (POS) a través del puerto serie, utilizando la **Web Serial API** del navegador.

## Características

- ✅ Conexión a balanza por puerto serie (COM7 en Windows, /dev/ttyUSB0 en Linux, etc.)
- ✅ Botón de conexión/desconexión en la barra del POS
- ✅ Indicador visual del estado de conexión
- ✅ Popup para visualizar peso y datos raw de la balanza
- ✅ Configuración de parámetros serie (baudRate, dataBits, stopBits, parity, flowControl)
- ✅ Regex configurable para extraer el peso del stream
- ✅ Degradación elegante si el navegador no soporta Web Serial API
- ✅ Integración con productos "a pesar"

## Requisitos

### Navegador
- **Chrome 89+**, **Edge 89+** o **Chromium** (Firefox y Safari NO soportan Web Serial API)
- Conexión **HTTPS** o acceso desde **localhost**

### Hardware
- Balanza con salida RS-232 o USB-Serie
- Cable serie o adaptador USB-Serie

### Odoo
- Odoo 19.0
- Módulo `point_of_sale`

## Instalación

1. Copiar el módulo a la carpeta de addons de Odoo:
   ```
   /odoo/custom/src/xtendoo/xtd_pos_serial_scale/
   ```

2. Actualizar la lista de módulos en Odoo

3. Instalar el módulo "POS Serial Scale - Web Serial API"

## Configuración

### En la configuración del Punto de Venta

1. Ir a **Punto de Venta > Configuración > Punto de Venta**
2. Seleccionar el POS a configurar
3. En la pestaña **Dispositivos conectados**, buscar la sección **Balanza Serie (Web Serial API)**
4. Configurar:
   - **Balanza Serie Habilitada**: Activar la integración
   - **Puerto (orientativo)**: Texto informativo (ej: COM7)
   - **Baud Rate**: Velocidad de transmisión (típico: 9600)
   - **Bits de Datos**: 7 u 8 bits
   - **Bits de Parada**: 1 o 2 bits
   - **Paridad**: Ninguno, Par (Even) o Impar (Odd)
   - **Control de Flujo**: Ninguno o Hardware (RTS/CTS)
   - **Regex para Peso**: Expresión regular para extraer el peso

### Regex por defecto

La regex por defecto `(-?\d+(?:[.,]\d+)?)` captura:
- Números enteros: `123`
- Números decimales con punto: `12.345`
- Números decimales con coma: `12,345`
- Números negativos: `-12.345`

### Ejemplos de formatos de balanza

| Balanza | Formato típico | Regex sugerida |
|---------|----------------|----------------|
| Genérica | `12.345 kg` | `(-?\d+(?:[.,]\d+)?)` |
| Con prefijo | `W: 12.345` | `W:\s*(-?\d+(?:[.,]\d+)?)` |
| Con estado | `ST,GS, 12.345 kg` | `(-?\d+\.\d+)\s*kg` |

## Uso en Windows (COM7)

### Prueba de conexión

1. Conectar la balanza al puerto COM7 (o verificar el puerto en Administrador de Dispositivos)
2. Abrir el POS en Chrome o Edge
3. Pulsar el botón **Balanza** (icono de balanza) en la barra superior
4. Pulsar **Conectar**
5. En el diálogo del navegador, seleccionar el puerto COM7
6. La balanza debe mostrar estado "Conectado"
7. Colocar un objeto en la balanza y verificar que se muestra el peso

### Solución de problemas

| Problema | Causa probable | Solución |
|----------|----------------|----------|
| "Navegador no compatible" | Firefox/Safari | Usar Chrome o Edge |
| "Permiso denegado" | Puerto bloqueado | Cerrar otras apps que usen el puerto |
| "Puerto ocupado" | Otra app usa COM7 | Cerrar HyperTerminal, PuTTY, etc. |
| No aparece peso | Regex incorrecta | Revisar formato de la balanza y ajustar regex |
| Datos corruptos | Parámetros incorrectos | Verificar baudRate, dataBits, parity |

## Limitaciones (Web Serial API)

1. **Requiere interacción del usuario**: La conexión debe iniciarse por un click (no automática)
2. **Sin persistencia**: El navegador no "recuerda" el puerto; hay que seleccionarlo cada sesión
3. **Solo Chrome/Edge**: Firefox y Safari no soportan la API
4. **HTTPS obligatorio**: En producción debe usarse HTTPS (localhost funciona sin HTTPS)

## Estructura del módulo

```
xtd_pos_serial_scale/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   └── pos_config.py
├── views/
│   └── pos_config_views.xml
├── static/
│   └── src/
│       ├── js/
│       │   ├── serial_scale_service.js
│       │   ├── serial_scale_popup.js
│       │   ├── serial_scale_button.js
│       │   └── pos_store_patch.js
│       ├── xml/
│       │   ├── serial_scale_popup.xml
│       │   ├── serial_scale_button.xml
│       │   └── navbar_patch.xml
│       └── scss/
│           └── serial_scale.scss
```

## Campos añadidos a pos.config

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `xtd_serial_scale_enabled` | Boolean | Activar integración |
| `xtd_serial_port_hint` | Char | Puerto orientativo (informativo) |
| `xtd_serial_baudrate` | Integer | Velocidad en baudios |
| `xtd_serial_databits` | Selection | Bits de datos (7/8) |
| `xtd_serial_stopbits` | Selection | Bits de parada (1/2) |
| `xtd_serial_parity` | Selection | Paridad (none/even/odd) |
| `xtd_serial_flowcontrol` | Selection | Control de flujo (none/hardware) |
| `xtd_serial_weight_regex` | Char | Regex para extraer peso |

## Licencia

LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl)

## Autor

Xtendoo - https://www.xtendoo.es

