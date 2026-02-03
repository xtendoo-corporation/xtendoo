# Xtendoo Scales

Módulo para Odoo 19 que mejora la integración de básculas USB con el Point of Sale.

## Problema que soluciona

Cuando se conecta una báscula USB al sistema, el peso enviado es capturado por el navegador como entrada de teclado. El servicio de códigos de barras de Odoo intenta interpretar este peso como un código de barras, causando errores y mostrando notificaciones de "código de barras no encontrado".

## Solución

Este módulo extiende el servicio `BarcodeReader` del POS para:

1. **Detectar entradas numéricas**: Identifica cuando la entrada capturada es solo un número (posiblemente peso de una báscula).
   - Soporta formato anglosajón con punto decimal: `1.5`, `0.385`, `123`
   - Soporta formato europeo con coma decimal: `1,5`, `0,385`, `123`

2. **Verificar contexto**: Antes de procesar como código de barras, verifica si:
   - Hay un campo de cantidad activo (con foco)
   - Hay una línea de pedido seleccionada
   - Hay un popup de cantidad visible

3. **Ignorar en contexto apropiado**: Si se detecta que la entrada numérica es para un campo de cantidad, la ignora y permite que se ingrese normalmente en el campo.

## Características

- ✅ Compatible con Odoo 19
- ✅ No modifica código core, usa sistema de parches
- ✅ Logging en consola para debugging
- ✅ Detecta múltiples tipos de campos de cantidad
- ✅ Detecta líneas de pedido seleccionadas
- ✅ Detecta popups de cantidad

## Instalación

1. El módulo ya está en la ruta: `odoo/custom/src/xtendoo/xtendoo_scales/`

2. Actualizar la lista de módulos en Odoo (Modo desarrollador):
   - Apps > Actualizar lista de aplicaciones

3. Buscar e instalar el módulo "Xtendoo Scales"

## Uso

Una vez instalado, el módulo funciona automáticamente:

1. Abre el POS
2. Selecciona un producto
3. Haz clic en el campo de cantidad (o la cantidad se selecciona automáticamente)
4. Coloca un producto en la báscula USB
5. El peso se ingresará en el campo de cantidad sin intentar buscar un código de barras

## Debugging

El módulo incluye mensajes de consola para ayudar en el debugging. Abre las herramientas de desarrollador del navegador (F12) y revisa la consola para ver:

- `[Xtendoo Scales] Servicio de báscula inicializado correctamente`
- `[Xtendoo Scales] Ignorando entrada numérica en campo de cantidad: XXX`
- `[Xtendoo Scales] Ignorando entrada numérica con línea de pedido seleccionada: XXX`

## Autor

**Xtendoo**
- Website: https://www.xtendoo.es

## Licencia

AGPL-3
