# Guía de Uso de los Logs de Depuración

## 🎯 Cómo Ver la Información de la Balanza

### Paso 1: Abrir la Consola del Navegador

1. Abrir el **POS** en Chrome o Edge
2. Presionar **F12** (o Ctrl+Shift+I)
3. Ir a la pestaña **Console**

### Paso 2: Conectar la Balanza

1. En el POS, hacer clic en el botón de **Balanza** (icono de báscula)
2. Hacer clic en **Conectar**
3. Seleccionar el puerto COM de la balanza en el diálogo del navegador

### Paso 3: Ver los Logs con Colores

Una vez conectada, verás este mensaje en la consola:

```
╔══════════════════════════════════════════════════════════════╗
║  🚀 BALANZA CONECTADA - INICIANDO LECTURA CONTINUA          ║
╚══════════════════════════════════════════════════════════════╝
⚙️  Configuración activa:
   • Baud Rate: 9600
   • Data Bits: 8
   • Stop Bits: 1
   • Parity: none
   • Regex: (-?\d+(?:[.,]\d+)?)
   • Unidad: kg

👀 Esperando datos de la balanza...
   (Coloca un peso en la balanza para ver los datos)
```

### Paso 4: Colocar Peso en la Balanza

Cuando coloques un objeto en la balanza, verás **logs con colores**:

---

## 📊 Tipos de Logs

### 🟢 Log Verde: DATOS RECIBIDOS

Cada vez que la balanza envía datos, verás un bloque verde con toda la información:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 DATOS RECIBIDOS DE LA BALANZA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Datos RAW (string): "ST,GS, 12.345 kg\r\n"
Datos RAW (JSON): "ST,GS, 12.345 kg\r\n"
Longitud: 18 caracteres
Bytes (hex): 53 54 2c 47 53 2c 20 31 32 2e 33 34 35 20 6b 67 0d 0a
Bytes (decimal): 83 84 44 71 83 44 32 49 50 46 51 52 53 32 107 103 13 10
```

**¿Qué significa cada línea?**
- **Datos RAW (string)**: El texto exacto que envió la balanza
- **Datos RAW (JSON)**: Lo mismo pero en formato JSON (útil para ver caracteres invisibles)
- **Longitud**: Cuántos caracteres tiene
- **Bytes (hex)**: Representación hexadecimal de cada carácter
- **Bytes (decimal)**: Representación decimal de cada carácter

---

### 🟣 Log Magenta: PROCESAMIENTO DE LÍNEA

Después del log verde, verás el procesamiento de cada línea:

```
╔════════════════════════════════════════════════════════╗
║  PROCESANDO LÍNEA DE LA BALANZA                       ║
╚════════════════════════════════════════════════════════╝
📝 Línea recibida: "ST,GS, 12.345 kg"
📏 Longitud: 16 caracteres
🔢 Bytes (hex): 53 54 2c 47 53 2c 20 31 32 2e 33 34 35 20 6b 67
🔤 Caracteres: 'S' 'T' ',' 'G' 'S' ',' ' ' '1' '2' '.' '3' '4' '5' ' ' 'k' 'g'
```

**Información útil:**
- **Línea recibida**: La línea completa (sin \r\n)
- **Caracteres**: Cada carácter separado (útil para ver espacios)

---

### 🟦 Log Cian: APLICACIÓN DE REGEX

```
🎯 Regex configurada: (-?\d+(?:[.,]\d+)?)
🔍 Resultado del match: ["12.345", "12.345"]
```

**Indica:**
- Qué regex se está usando
- Si encontró coincidencia (array con resultados) o no (null)

---

### ✅ Log Verde Grande: PESO ENCONTRADO

Si la regex funciona correctamente:

```
✅ MATCH ENCONTRADO!
  ➜ String extraído: "12.345"
  ➜ String normalizado: "12.345"
  ➜ Peso parseado (raw): 12.345
  ➜ Unidad configurada: kg

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ✓ PESO ACTUALIZADO: 12.345 kg         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**¡Esto significa que TODO está funcionando correctamente!** 🎉

**Si ves conversión de unidades:**
```
  ➜ Conversión: 12345 gramos → 12.345 kg
```

---

### ❌ Log Rojo: NO SE ENCONTRÓ PESO

Si la regex NO funciona:

```
❌ NO SE ENCONTRÓ PESO EN LA LÍNEA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 SUGERENCIAS PARA SOLUCIONAR:
  1️⃣  Verifica que la regex sea correcta para tu balanza
  2️⃣  Formato actual de la línea: "ST,GS, 12.345 kg"
  3️⃣  Regex actual: (-?\d+(?:[.,]\d+)?)
  4️⃣  Se encontró este número en la línea: "12.345"
     💡 ¿Es este el peso? Prueba esta regex: (\d+\.\d+)
     💡 O esta más genérica: (\d+[.,]?\d*)
  5️⃣  EJEMPLOS DE REGEX COMUNES:
     • Para '12.345': (\d+[.,]\d+)
     • Para 'W: 12.345': W:\s*(\d+[.,]\d+)
     • Para 'ST,GS, 12.345 kg': (\d+[.,]\d+)
     • Para 'NET 12,345': NET\s+(\d+,\d+)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**El sistema te ayuda automáticamente:**
- Muestra el formato exacto que recibió
- Te dice qué número encontró
- Te sugiere regex que podrían funcionar
- Te da ejemplos según el formato detectado

---

## 🔍 Casos de Uso Comunes

### Caso 1: Ver Qué Está Enviando la Balanza

**Problema:** No sé qué formato usa mi balanza

**Solución:**
1. Conectar la balanza
2. Colocar peso
3. Buscar en la consola: **"🎯 DATOS RECIBIDOS"** (verde)
4. Copiar el contenido de **"Datos RAW (string)"**
5. Ese es el formato exacto de tu balanza

**Ejemplo:**
```
Datos RAW (string): "W: 12.345 kg\r\n"
```
→ Tu balanza envía: **W: 12.345 kg**

---

### Caso 2: La Balanza Envía Datos Pero No Se Lee el Peso

**Problema:** Veo logs verdes pero no el mensaje "✓ PESO ACTUALIZADO"

**Solución:**
1. Buscar el mensaje rojo: **"❌ NO SE ENCONTRÓ PESO"**
2. Leer las sugerencias automáticas
3. Copiar la regex sugerida (aparece con 💡)
4. Ir a configuración del POS → Campo "Regex para Peso"
5. Pegar la nueva regex
6. Guardar y reiniciar el POS

---

### Caso 3: Verificar los Parámetros de Comunicación

**Problema:** Recibo caracteres extraños o basura

**Solución:**
1. Ver el log de inicio (verde con 🚀)
2. Verificar los parámetros:
   ```
   • Baud Rate: 9600
   • Data Bits: 8
   • Stop Bits: 1
   • Parity: none
   ```
3. Compararlos con el manual de la balanza
4. Ajustar en configuración del POS si no coinciden

**Bytes extraños indican:**
- Baud Rate incorrecto (números al azar)
- Paridad incorrecta (símbolos raros)
- Data Bits incorrectos (letras sin sentido)

---

### Caso 4: La Balanza Envía en Gramos

**Problema:** Veo números muy grandes (12345 en lugar de 12.345)

**Solución:**
Ver el log de procesamiento:
```
✅ MATCH ENCONTRADO!
  ➜ Peso parseado (raw): 12345
  ➜ Unidad configurada: kg
```

Si el peso es en gramos:
1. Ir a configuración del POS
2. Campo **"Unidad de Peso"**: cambiar a **"Gramos (g)"**
3. Guardar y reiniciar

Ahora verás:
```
  ➜ Conversión: 12345 gramos → 12.345 kg
```

---

### Caso 5: No Veo Ningún Log

**Problema:** La balanza está "conectada" pero no hay logs

**Posibles causas:**

1. **La balanza no envía datos automáticamente**
   - Algunas balanzas solo envían al presionar un botón
   - Buscar botón "PRINT" o "SEND" en la balanza
   - Configurar la balanza en modo "stream continuo"

2. **Puerto incorrecto**
   - Verificar en Administrador de Dispositivos (Windows) el puerto COM real
   - Puede que sea COM3, COM4, etc., no COM7

3. **Cable desconectado o roto**
   - Verificar conexión física
   - Probar con otro cable

4. **Balanza apagada o en modo sleep**
   - Encender la balanza
   - Colocar peso para activarla

---

## 🎨 Significado de los Colores

- 🟢 **Verde**: Información de datos recibidos, conexión exitosa, peso actualizado
- 🟣 **Magenta**: Procesamiento de líneas
- 🟦 **Cian**: Aplicación de regex, configuración
- 🟡 **Amarillo**: Advertencias, sugerencias, ayuda
- 🔴 **Rojo**: Errores, problemas, no se encontró peso

---

## 📋 Checklist de Depuración

Usa este checklist cuando depures:

- [ ] La consola del navegador está abierta (F12)
- [ ] La balanza está conectada (ves el log con 🚀)
- [ ] Colocaste peso en la balanza
- [ ] Ves logs verdes "🎯 DATOS RECIBIDOS"
- [ ] Los datos tienen sentido (no son basura)
- [ ] Ves el log magenta "PROCESANDO LÍNEA"
- [ ] Identificaste el formato exacto en "Línea recibida"
- [ ] Ves el log "✅ MATCH ENCONTRADO"
- [ ] Ves el log grande "✓ PESO ACTUALIZADO"

**Si alguno falla, ese es el punto del problema.**

---

## 💡 Consejos Pro

### Copiar Logs para Soporte

1. Clic derecho en la consola → **Save as...**
2. Guardar el archivo `.log`
3. Enviar a soporte técnico

### Filtrar Logs

En la consola, escribe en el filtro:
- `SerialScaleService` - Ver solo logs de la balanza
- `DATOS RECIBIDOS` - Ver solo datos entrantes
- `PESO ACTUALIZADO` - Ver solo cuando se captura peso
- `NO SE ENCONTRÓ` - Ver solo errores de regex

### Limpiar la Consola

- Clic en el icono 🚫 (Clear console)
- O presionar Ctrl+L
- Útil antes de hacer una nueva prueba

---

## 🆘 Problemas Frecuentes

| Síntoma | Causa | Solución |
|---------|-------|----------|
| No hay logs verdes | Balanza no envía datos | Verificar conexión, presionar botón PRINT |
| Logs con símbolos raros | Parámetros incorrectos | Ajustar Baud Rate, Parity, Data Bits |
| Logs correctos pero sin peso | Regex incorrecta | Usar sugerencias automáticas en rojo |
| Peso multiplicado por 1000 | Unidad incorrecta | Cambiar de kg a gramos en configuración |
| Logs intermitentes | Cable suelto | Verificar conexión física |

---

## 📞 Contactar Soporte

Si después de revisar los logs aún tienes problemas, envía:

1. ✅ Captura de pantalla de la consola completa
2. ✅ Marca y modelo de la balanza
3. ✅ Configuración actual del POS (captura)
4. ✅ Archivo de logs exportado (Save as...)

Esto ayudará a diagnosticar el problema rápidamente.

---

**¡Ahora tienes toda la información visible en la consola para diagnosticar cualquier problema!** 🎉

