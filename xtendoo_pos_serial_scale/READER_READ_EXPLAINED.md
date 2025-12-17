# Documentación: reader.read() - Qué Devuelve y Cómo Funciona

## 🔍 ¿Qué es `reader.read()`?

`reader.read()` es un método de la **Web Streams API** que lee datos del puerto serie de forma asíncrona.

```javascript
const { value, done } = await this.reader.read();
```

---

## 📊 Valores que Devuelve

### Estructura del Objeto Devuelto

`reader.read()` devuelve una **Promise** que se resuelve en un objeto con dos propiedades:

```javascript
{
    value: string | undefined,  // Los datos leídos (puede ser undefined)
    done: boolean              // true si el stream terminó, false si hay más datos
}
```

---

## 🎯 Propiedad `value`

### Tipo de Dato
- **Tipo**: `string` (texto)
- **Contenido**: Los caracteres recibidos del puerto serie

### Valores Posibles

#### 1. String con datos (CASO NORMAL)
```javascript
value: "12.345 kg\r\n"
typeof value: "string"
value.length: 11
```

#### 2. String vacío (sin datos en este ciclo)
```javascript
value: ""
typeof value: "string"
value.length: 0
```

#### 3. undefined (stream cerrado)
```javascript
value: undefined
typeof value: "undefined"
```

### Ejemplos Reales

**Balanza que envía continuamente:**
```javascript
// Lectura #1
{ value: "ST,GS, 12.345 kg\r\n", done: false }

// Lectura #2 (después de cambiar el peso)
{ value: "ST,GS, 15.678 kg\r\n", done: false }

// Lectura #3
{ value: "ST,GS, 15.678 kg\r\n", done: false }
```

**Balanza que envía solo al presionar botón:**
```javascript
// Lectura #1 (sin botón presionado - esperando datos)
// (await se queda esperando hasta que lleguen datos)

// Lectura #2 (botón presionado)
{ value: "W: 12.345\r\n", done: false }
```

**Stream cerrado:**
```javascript
{ value: undefined, done: true }
```

---

## 🎯 Propiedad `done`

### Tipo de Dato
- **Tipo**: `boolean`
- **Contenido**: Indica si el stream ha terminado

### Valores Posibles

#### `done: false` (CASO NORMAL)
El stream está activo y puede haber más datos.

```javascript
{ value: "12.345 kg", done: false }
```

**Significado**:
- ✅ El puerto está abierto
- ✅ Puede haber más lecturas
- ✅ Continuar el bucle `while`

#### `done: true` (STREAM CERRADO)
El stream se cerró (puerto desconectado).

```javascript
{ value: undefined, done: true }
```

**Significado**:
- ❌ El puerto se cerró
- ❌ No habrá más datos
- ❌ Salir del bucle `while`

**Causas de `done: true`:**
- Usuario desconectó la balanza
- Cable desenchufado
- Balanza apagada
- Llamada a `disconnect()` desde código

---

## 🔄 Flujo de Lectura Completo

### Ciclo Normal de Lectura

```javascript
// ITERACIÓN 1
📥 LECTURA #1 - Esperando datos del puerto serie...
// await reader.read() se BLOQUEA aquí hasta que lleguen datos

// LA BALANZA ENVÍA: "12.345 kg\r\n"

▼▼▼ READER.READ() DEVOLVIÓ:
   • done: false (boolean)
   • value: "12.345 kg\r\n" (string)
   • value.length: 11 caracteres
▲▲▲

// Se procesa con _processIncomingData()

// ITERACIÓN 2
📥 LECTURA #2 - Esperando datos del puerto serie...
// await reader.read() se BLOQUEA otra vez...

// LA BALANZA ENVÍA: "12.345 kg\r\n"

▼▼▼ READER.READ() DEVOLVIÓ:
   • done: false (boolean)
   • value: "12.345 kg\r\n" (string)
   • value.length: 11 caracteres
▲▲▲

// Y así continúa...
```

### Cuando se Desconecta

```javascript
// ITERACIÓN N
📥 LECTURA #N - Esperando datos del puerto serie...

// USUARIO DESCONECTA LA BALANZA

▼▼▼ READER.READ() DEVOLVIÓ:
   • done: true (boolean)
   • value: undefined (undefined)
▲▲▲

[SerialScaleService] Stream cerrado por el dispositivo
// Sale del bucle while
```

---

## 🧩 ¿Por Qué es Asíncrono (await)?

`reader.read()` es **asíncrono** porque:

1. **Espera datos**: Si no hay datos, se queda esperando (no bloquea el navegador)
2. **No satura CPU**: No hace un bucle infinito consumiendo recursos
3. **Devuelve control**: El navegador puede hacer otras cosas mientras espera

### Sin await (INCORRECTO)
```javascript
const result = this.reader.read(); // ❌ devuelve Promise, no los datos
console.log(result); // Promise { <pending> }
```

### Con await (CORRECTO)
```javascript
const { value, done } = await this.reader.read(); // ✅ espera y obtiene los datos
console.log(value); // "12.345 kg\r\n"
```

---

## 📝 Comportamiento de `reader.read()` según el Dispositivo

### Balanza en Modo Stream Continuo

**Configuración**: La balanza envía peso constantemente cada X ms

```javascript
// Lectura #1 (inmediata)
{ value: "12.345 kg\r\n", done: false }

// Lectura #2 (200ms después)
{ value: "12.345 kg\r\n", done: false }

// Lectura #3 (200ms después)
{ value: "12.345 kg\r\n", done: false }

// ... continúa cada 200ms
```

**Log en consola:**
```
📥 LECTURA #1 - Esperando datos...
▼▼▼ READER.READ() DEVOLVIÓ:
   • value: "12.345 kg\r\n"
▲▲▲

📥 LECTURA #2 - Esperando datos...
▼▼▼ READER.READ() DEVOLVIÓ:
   • value: "12.345 kg\r\n"
▲▲▲

📥 LECTURA #3 - Esperando datos...
▼▼▼ READER.READ() DEVOLVIÓ:
   • value: "12.345 kg\r\n"
▲▲▲
```

### Balanza en Modo Manual (Botón PRINT)

**Configuración**: La balanza solo envía al presionar botón

```javascript
// Lectura #1 (esperando... puede tardar minutos)
// await se queda esperando hasta que el usuario presiona PRINT

// USUARIO PRESIONA PRINT
{ value: "12.345 kg\r\n", done: false }

// Lectura #2 (esperando otra vez...)
// await se queda esperando...
```

**Log en consola:**
```
📥 LECTURA #1 - Esperando datos...
(silencio... esperando que presiones el botón)

// PRESIONAS PRINT

▼▼▼ READER.READ() DEVOLVIÓ:
   • value: "12.345 kg\r\n"
▲▲▲

📥 LECTURA #2 - Esperando datos...
(esperando otra vez...)
```

### Balanza que Envía Múltiples Líneas a la Vez

**Configuración**: La balanza acumula datos y los envía en bloque

```javascript
// Lectura #1
{
    value: "TARE: 1.234\r\nGROSS: 13.579\r\nNET: 12.345\r\n",
    done: false
}
```

**Log en consola:**
```
📥 LECTURA #1 - Esperando datos...
▼▼▼ READER.READ() DEVOLVIÓ:
   • value: "TARE: 1.234\r\nGROSS: 13.579\r\nNET: 12.345\r\n"
   • value.length: 48 caracteres
▲▲▲

🎯 DATOS RECIBIDOS DE LA BALANZA
Datos RAW: "TARE: 1.234\r\nGROSS: 13.579\r\nNET: 12.345\r\n"

📋 Líneas completas encontradas: 3
  Línea 1: "TARE: 1.234"
  Línea 2: "GROSS: 13.579"
  Línea 3: "NET: 12.345"
```

---

## 🎯 Casos Especiales

### Caso 1: Fragmentación de Datos

A veces `reader.read()` devuelve datos **fragmentados**:

```javascript
// Lectura #1 - Solo recibe parte del mensaje
{ value: "12.3", done: false }

// Lectura #2 - Recibe el resto
{ value: "45 kg\r\n", done: false }
```

**Solución**: El `inputBuffer` en `_processIncomingData()` acumula los fragmentos hasta formar líneas completas.

### Caso 2: Múltiples Mensajes en un Solo Read

```javascript
// Lectura #1 - Varios mensajes juntos
{ value: "12.345\r\n12.345\r\n12.345\r\n", done: false }
```

**Solución**: El método `split(/\r?\n/)` separa en líneas individuales.

### Caso 3: Datos sin Salto de Línea

```javascript
// Lectura #1
{ value: "12.345 kg", done: false }

// Lectura #2
{ value: "13.456 kg", done: false }
```

**Problema**: Sin `\r\n`, no se puede detectar dónde termina un mensaje.

**Solución**:
- Configurar la balanza para enviar `\r\n`
- O modificar el código para procesar por tiempo/patrón

---

## 🔬 Análisis Técnico: TextDecoderStream

Antes de `reader.read()`, los datos pasan por un `TextDecoderStream`:

```javascript
const decoder = new TextDecoderStream();
this.readableStreamClosed = this.port.readable.pipeTo(decoder.writable);
this.reader = decoder.readable.getReader();
```

**¿Qué hace?**
1. `port.readable` → bytes raw del puerto serie
2. `TextDecoderStream` → convierte bytes a texto (UTF-8)
3. `reader.read()` → lee el texto convertido

**Ejemplo:**

```
Puerto Serie (bytes):    [53 54 2c 31 32 2e 33 34 35 0d 0a]
                         ↓ TextDecoderStream ↓
reader.read() (string):  "ST,12.345\r\n"
```

---

## 📊 Tabla Resumen

| Propiedad | Tipo | Valores Posibles | Significado |
|-----------|------|------------------|-------------|
| `value` | `string \| undefined` | `"12.345 kg"` | Datos recibidos |
| | | `""` | Sin datos (raro) |
| | | `undefined` | Stream cerrado |
| `done` | `boolean` | `false` | Stream activo |
| | | `true` | Stream cerrado |

---

## 🎯 Qué Verás en los Logs

Con los nuevos logs agregados, verás:

```
📥 LECTURA #1 - Esperando datos del puerto serie...

▼▼▼ READER.READ() DEVOLVIÓ:
   • done: false (boolean)
   • value: "ST,GS, 12.345 kg\r\n" (string)
   • value.length: 18 caracteres
   • value (preview): "ST,GS, 12.345 kg\r\n"
▲▲▲
```

**Esto te dice:**
- ✅ Cuántas veces se llamó a `read()` (contador)
- ✅ Si el stream está abierto (`done: false`)
- ✅ Qué datos llegaron exactamente (`value`)
- ✅ Cuántos caracteres tiene
- ✅ Vista previa del contenido

---

## 🆘 Problemas Comunes

### No veo ningún log de "LECTURA #1"

**Causa**: La conexión falló antes de iniciar la lectura

**Solución**: Verificar que veas el log "🚀 BALANZA CONECTADA"

### Veo "LECTURA #1" pero nunca "DEVOLVIÓ"

**Causa**: `await reader.read()` está esperando datos que nunca llegan

**Posibles motivos**:
- Balanza en modo manual (necesita presionar botón)
- Cable desconectado
- Balanza apagada
- Parámetros incorrectos (baudrate, etc.)

**Solución**: Presionar botón PRINT en la balanza o verificar conexión

### `done: true` inmediatamente

**Causa**: El puerto se cerró justo después de conectar

**Solución**: Verificar que el puerto no esté siendo usado por otra aplicación

### `value: undefined` siempre

**Causa**: Stream cerrado

**Solución**: Reconectar la balanza

---

## 💡 Tips para Depuración

1. **Cuenta las lecturas**: El número te dice si la balanza está enviando continuamente o solo al presionar botón
2. **Mide el tiempo**: Si tarda mucho entre lecturas, puede ser modo manual
3. **Revisa `value.length`**: Si es muy pequeño (1-2 chars), puede estar fragmentado
4. **Busca patrones**: ¿Siempre el mismo `value`? La balanza envía el mismo peso

---

## ✅ Conclusión

Ahora con los logs agregados puedes ver:

1. ✅ Cuántas veces se llama `reader.read()`
2. ✅ Qué devuelve cada llamada (`value` y `done`)
3. ✅ Si hay datos o está esperando
4. ✅ El flujo completo desde la lectura hasta el procesamiento

**¡Ya no perderás el seguimiento!** 🎉

