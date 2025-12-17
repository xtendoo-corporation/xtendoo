# Ejemplos de Regex para Balanzas Comunes

Este archivo contiene ejemplos de expresiones regulares (regex) para configurar diferentes modelos de balanzas en el módulo POS Serial Scale.

## Cómo usar este archivo

1. Identifica el formato de datos que envía tu balanza (ver consola del navegador)
2. Busca un formato similar en este archivo
3. Copia la regex correspondiente
4. Pégala en el campo "Regex para Peso" en la configuración del POS

---

## Formato Genérico

### Simple número decimal
```
Formato: 12.345
Regex: (-?\d+(?:[.,]\d+)?)
```

### Número con espacios
```
Formato:    12.345
Regex: (-?\d+(?:[.,]\d+)?)
```

### Número con signo
```
Formato: +12.345 o -12.345
Regex: [+-]?(\d+[.,]\d+)
```

---

## Formatos con Unidades

### Número seguido de kg
```
Formato: 12.345 kg
Regex: (\d+[.,]\d+)\s*kg
```

### Número seguido de g (gramos)
```
Formato: 12345 g
Regex: (\d+)\s*g
Nota: Configurar "Unidad de Peso" = "Gramos (g)" para conversión automática
```

### Número con KG mayúsculas
```
Formato: 12.345 KG
Regex: (\d+[.,]\d+)\s*KG
```

---

## Formatos con Prefijos

### Prefijo W: (Weight)
```
Formato: W: 12.345
Regex: W:\s*(\d+[.,]\d+)
```

### Prefijo WT o WEIGHT
```
Formato: WT 12.345 o WEIGHT 12.345
Regex: W(?:T|EIGHT)?\s+(\d+[.,]\d+)
```

### Prefijo NET (peso neto)
```
Formato: NET 12.345
Regex: NET\s+(\d+[.,]\d+)
```

### Prefijo GS (Gross/Stable)
```
Formato: GS 12.345
Regex: GS\s+(\d+[.,]\d+)
```

---

## Balanzas Específicas

### Toledo Scale
```
Formato: +00012.345kg o -00012.345kg
Regex: [+-]?0*(\d+\.\d+)kg
Baudrate: 9600
Data bits: 7
Parity: Even
Stop bits: 1
```

### Mettler Toledo
```
Formato: S S 00012.345 kg
Regex: S\s+S\s+0*(\d+\.\d+)
Baudrate: 9600
Data bits: 8
Parity: None
```

### Bizerba
```
Formato: 12.345 KG ST
Regex: (\d+\.\d+)\s+KG
Baudrate: 9600
```

### Sartorius
```
Formato: S 12.345 g
Regex: S\s+(\d+[.,]\d+)\s*g
Unidad: Gramos
```

### Ohaus
```
Formato: 12.345 g S
Regex: (\d+[.,]\d+)\s*g
Unidad: Gramos
```

### AND (A&D)
```
Formato: ST,GS, 12.345 kg
Regex: ST,GS,\s*(\d+[.,]\d+)
o más simple: (\d+[.,]\d+)\s*kg
```

### DIGI SM-100
```
Formato: 12345 (en gramos)
Regex: (\d+)
Unidad: Gramos
```

### CAS
```
Formato: 12.345KG
Regex: (\d+[.,]\d+)KG
```

### Excell
```
Formato: ST,  12.345 kg
Regex: ST,\s*(\d+[.,]\d+)
```

---

## Formatos Complejos

### Con múltiples campos separados por comas
```
Formato: ST,GS,12.345,kg
Regex: ST,GS,(\d+[.,]\d+),kg
```

### Con espacios y texto adicional
```
Formato: Weight: 12.345 kg Stable
Regex: Weight:\s*(\d+[.,]\d+)
```

### Con ceros a la izquierda
```
Formato: 00012.345
Regex: 0*(\d+[.,]\d+)
```

### Con formato de moneda (punto como separador de miles)
```
Formato: 1,234.567 (NO RECOMENDADO - puede causar confusión)
Regex: (\d+,\d+\.\d+)
Nota: Deberás procesar manualmente el separador de miles
```

---

## Casos Especiales

### Balanza que envía tara y neto
```
Formato: T:1.234 N:12.345
Regex para peso neto: N:(\d+[.,]\d+)
Regex para tara: T:(\d+[.,]\d+)
Nota: Actualmente solo se captura un peso. Usar el neto (N:)
```

### Balanza con caracteres de control
```
Formato: \x02 12.345 \x03 (STX y ETX)
Regex: (\d+[.,]\d+)
Nota: Los caracteres de control se ignoran automáticamente
```

### Balanza con formato hexadecimal
```
Formato: No soportado directamente
Solución: Configurar la balanza para enviar ASCII
```

---

## Regex para Validación de Números

### Solo números positivos
```
Regex: (\d+[.,]\d+)
```

### Números positivos y negativos
```
Regex: (-?\d+[.,]\d+)
```

### Con signo obligatorio
```
Regex: ([+-]\d+[.,]\d+)
```

### Números enteros (sin decimales)
```
Regex: (\d+)
```

### Con exactamente 3 decimales
```
Regex: (\d+[.,]\d{3})
```

### Con 1 a 3 decimales
```
Regex: (\d+[.,]\d{1,3})
```

---

## Herramientas de Prueba

### Probar regex online
- https://regex101.com/
- https://regexr.com/

### Ejemplo de uso en regex101.com:

1. Pega tu regex en el campo "Regular Expression"
2. Pega ejemplos de líneas de tu balanza en "Test String"
3. Verifica que el grupo de captura 1 contenga solo el número del peso
4. Si no funciona, ajusta la regex

---

## Tips para Crear tu Propia Regex

### Componentes básicos:

- `\d` = un dígito (0-9)
- `\d+` = uno o más dígitos
- `\d{3}` = exactamente 3 dígitos
- `[.,]` = punto o coma
- `\s` = espacio en blanco
- `\s*` = cero o más espacios
- `\s+` = uno o más espacios
- `?` = opcional (0 o 1 vez)
- `*` = cero o más veces
- `+` = una o más veces
- `()` = grupo de captura (IMPORTANTE)
- `[+-]` = signo más o menos
- `[-?]` = signo menos opcional

### Estructura básica:

```
[prefijo opcional] (número con decimales) [sufijo opcional]
```

### Ejemplos paso a paso:

#### Ejemplo 1: "W: 12.345 kg"

1. Prefijo: `W:\s*` (W: seguido de espacios opcionales)
2. Número: `(\d+\.\d+)` (dígitos, punto, dígitos) - EN PARÉNTESIS
3. Sufijo: `\s*kg` (espacios opcionales y kg)
4. Regex final: `W:\s*(\d+\.\d+)\s*kg`

#### Ejemplo 2: "ST,GS, 12.345 kg"

1. Prefijo: `ST,GS,\s*` (ST,GS, seguido de espacios)
2. Número: `(\d+[.,]\d+)` (acepta punto o coma)
3. Sufijo: `\s*kg`
4. Regex final: `ST,GS,\s*(\d+[.,]\d+)\s*kg`

O más simple si el peso siempre está antes de kg:
```
Regex: (\d+[.,]\d+)\s*kg
```

---

## Problemas Comunes

### La regex no captura nada
- Verifica que uses paréntesis `()` alrededor del número
- Asegúrate de escapar caracteres especiales con `\`
- Comprueba que la regex coincida EXACTAMENTE con el formato

### Captura texto adicional
- Asegúrate de que solo el número esté dentro de `()`
- Usa `\s*` para espacios opcionales
- Usa `\d` en lugar de `.` para evitar capturar cualquier carácter

### No reconoce decimales con coma
- Usa `[.,]` en lugar de solo `.`
- Ejemplo: `(\d+[.,]\d+)` en lugar de `(\d+\.\d+)`

### Captura ceros a la izquierda
- Usa `0*` antes del número para ignorarlos
- Ejemplo: `0*(\d+\.\d+)`

---

## Soporte

Si tu balanza no aparece en esta lista:

1. Consulta el manual de la balanza para conocer el formato de salida
2. Usa la consola del navegador para ver qué envía la balanza
3. Prueba la regex en regex101.com antes de configurarla en Odoo
4. Consulta el archivo TROUBLESHOOTING.md para más ayuda
5. Contacta con soporte técnico adjuntando el formato exacto de tu balanza

