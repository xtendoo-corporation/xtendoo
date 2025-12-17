# Guía de Solución de Problemas - Balanza Serie POS

## Problema: "La balanza conecta pero no lee el peso"

### Diagnóstico Rápido

#### Paso 1: Verificar que la balanza está enviando datos

1. Abrir el **POS** en Chrome/Edge
2. Presionar **F12** para abrir las herramientas de desarrollo
3. Ir a la pestaña **Console**
4. Conectar la balanza usando el botón en el POS
5. Colocar un peso en la balanza
6. Buscar en la consola líneas como:

```
[SerialScaleService] Datos RAW recibidos: "ST,GS, 12.345 kg\r\n"
[SerialScaleService] Líneas encontradas: 1
[SerialScaleService] Línea recibida: ST,GS, 12.345 kg
```

**¿Ves estos mensajes?**
- ✅ **SÍ** → La balanza está enviando datos. Pasa al Paso 2.
- ❌ **NO** → La balanza no envía datos o los parámetros serie son incorrectos.

---

#### Paso 2: Verificar los parámetros de comunicación

Si no recibes datos o recibes caracteres extraños:

**Revisar en la configuración del POS:**
- **Baud Rate**: Debe coincidir con la balanza (típico: 9600, 19200, 38400)
- **Bits de Datos**: Normalmente 8 bits
- **Paridad**: Normalmente "Ninguno"
- **Bits de Parada**: Normalmente 1 bit

**Consultar el manual de la balanza** para obtener estos valores.

---

#### Paso 3: Analizar el formato de datos recibidos

En la consola, busca:

```
[SerialScaleService] Línea recibida: <AQUÍ EL FORMATO DE TU BALANZA>
```

**Ejemplos de formatos comunes:**

| Formato | Ejemplo real | Regex sugerida |
|---------|--------------|----------------|
| Simple decimal | `12.345` | `(-?\d+(?:[.,]\d+)?)` |
| Con unidad | `12.345 kg` | `(-?\d+(?:[.,]\d+)?)` |
| Con prefijo W | `W: 12.345` | `W:\s*(-?\d+(?:[.,]\d+)?)` |
| Con estado ST | `ST,GS, 12.345 kg` | `(\d+\.\d+)` |
| Con NET | `NET 12,345` | `NET\s+(\d+,\d+)` |
| Toledo | `+00012.345kg` | `[+-]?(\d+\.\d+)` |
| Mettler Toledo | `S S 00012.345 kg` | `S\s+S\s+(\d+\.\d+)` |
| Bizerba | `12.345 KG ST` | `(\d+\.\d+)\s+KG` |

---

#### Paso 4: Ajustar la expresión regular (Regex)

1. Ir a **Punto de Venta > Configuración > Punto de Venta**
2. Editar la configuración del POS
3. Buscar el campo **Regex para Peso**
4. Modificar según el formato de tu balanza (ver tabla arriba)
5. **IMPORTANTE**: Los paréntesis `()` deben rodear el número del peso

**Ejemplo:**
- Formato recibido: `ST,GS, 12.345 kg`
- Regex: `(\d+\.\d+)` o `(\d+[.,]\d+)`

---

#### Paso 5: Verificar que la regex captura el peso

Después de cambiar la regex:

1. Reiniciar el POS
2. Conectar la balanza
3. Colocar peso
4. Buscar en la consola:

```
[SerialScaleService] Resultado del match: ["12.345", "12.345"]
[SerialScaleService] ✓ PESO ACTUALIZADO: 12.345 kg
```

**¿Ves el mensaje "✓ PESO ACTUALIZADO"?**
- ✅ **SÍ** → ¡Problema resuelto!
- ❌ **NO** → La regex aún no es correcta. Ver Paso 6.

---

#### Paso 6: Uso del asistente de depuración

Si la regex no funciona, la consola te dará pistas:

```
[SerialScaleService] ✗ No se encontró peso en la línea
[SerialScaleService] Sugerencias:
  1. Verifica que la regex sea correcta para tu balanza
  2. Formato actual de la línea: ST,GS, 12.345 kg
  3. Regex actual: (-?\d+(?:[.,]\d+)?)
  4. Se encontró este número en la línea: 12.345
     ¿Es este el peso? Ajusta la regex en la configuración del POS
```

El sistema te muestra **exactamente** qué número encontró. Si es correcto, ajusta la regex para capturarlo.

---

### Casos Especiales

#### La balanza envía en gramos pero quiero kg

1. Ir a configuración del POS
2. Campo **Unidad de Peso**: seleccionar "Gramos (g)"
3. El sistema convertirá automáticamente a kg

**Ejemplo:**
- Balanza envía: `12345` (gramos)
- Sistema convierte: `12.345` kg

#### La balanza envía múltiples líneas o datos continuos

El sistema procesa líneas completas (terminadas en `\n` o `\r\n`). Si la balanza envía datos continuos sin saltos de línea, puede ser necesario:

1. Configurar la balanza para que envíe líneas completas
2. O modificar la regex para capturar datos en flujo continuo

---

### Ejemplos Reales de Configuración

#### Balanza Genérica (9600, 8N1)
```
Baud Rate: 9600
Bits de Datos: 8
Paridad: Ninguno
Bits de Parada: 1
Regex: (-?\d+(?:[.,]\d+)?)
Unidad: kg
```

#### Toledo Scale
```
Baud Rate: 9600
Bits de Datos: 7
Paridad: Par (Even)
Bits de Parada: 1
Regex: [+-]?(\d+\.\d+)
Unidad: kg
```

#### Mettler Toledo
```
Baud Rate: 9600
Bits de Datos: 8
Paridad: Ninguno
Bits de Parada: 1
Regex: S\s+S\s+(\d+\.\d+)
Unidad: kg
```

---

### Aún tengo problemas

Si después de seguir todos los pasos el problema persiste:

1. **Exportar los logs de la consola**:
   - En la consola del navegador, clic derecho → "Save as..."
   - Guardar el archivo de logs

2. **Recopilar información**:
   - Marca y modelo de la balanza
   - Configuración actual del POS (captura de pantalla)
   - Logs de la consola
   - Ejemplo de datos que envía la balanza

3. **Contactar con soporte técnico** proporcionando toda la información anterior

---

### Comandos Útiles para Probar la Balanza (Windows)

#### Usando PowerShell para leer el puerto COM7:

```powershell
$port = new-Object System.IO.Ports.SerialPort COM7,9600,None,8,One
$port.Open()
while($true) {
    $line = $port.ReadLine()
    Write-Host $line
}
```

Esto te permite ver **exactamente** qué datos envía la balanza sin Odoo.

---

## Checklist de Diagnóstico

- [ ] La balanza está conectada físicamente al puerto COM
- [ ] En Administrador de Dispositivos (Windows) aparece el puerto COM
- [ ] El POS se abre en Chrome/Edge (no Firefox/Safari)
- [ ] La conexión es HTTPS o localhost
- [ ] El módulo está instalado y habilitado en el POS
- [ ] Se abre la consola del navegador (F12)
- [ ] Se conecta la balanza y se ve el mensaje de conexión exitosa
- [ ] Se coloca peso en la balanza
- [ ] Se ven logs "Datos RAW recibidos" en la consola
- [ ] Se identifica el formato exacto de la línea recibida
- [ ] Se configura la regex correcta para ese formato
- [ ] Se reinicia el POS después de cambiar la configuración
- [ ] Se ve el mensaje "✓ PESO ACTUALIZADO" en la consola

Si todos los pasos están marcados y aún no funciona, puede ser un problema de hardware o drivers.

