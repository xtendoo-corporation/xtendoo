# Xtendoo Open Cash Drawer

Módulo para abrir el cajón portamonedas desde el **Punto de Venta (TPV)** en Odoo 19  
**sin necesidad de imprimir ningún ticket** (siempre que sea posible).

---

## ¿Por qué evitar la impresión?

El método tradicional de apertura del cajón consiste en enviar un trabajo de
impresión a la impresora para que ésta, al finalizar, emita el pulso eléctrico
que abre el cajón.  Esto tiene varios inconvenientes:

* Consume papel y realiza un corte innecesario.
* Introduce latencia (la impresora debe procesar el trabajo completo).
* Puede fallar si la impresora está ocupada o sin papel.

La solución óptima es enviar **directamente los bytes del comando ESC/POS** al
pin del cajón (`ESC p`, bytes `27 112 0 25 250`) sin envolver esos bytes en un
trabajo de impresión.

---

## Estrategias de apertura (en orden de prioridad)

| # | Estrategia | Imprime | Requisito |
|---|-----------|---------|-----------|
| **P1** | `openCashbox()` nativo del dispositivo ePOS | ❌ No | SDK ePOS de Epson/Star conectado al navegador |
| **P2** | Comando ESC/POS directo desde el servidor Odoo | ❌ No | Configurar **Dirección de la impresora del cajón** |
| **P3** | Hardware proxy / IoT Box de Odoo | ❌ No | IoT Box configurado con `iface_cashdrawer` |
| **P4** | Impresión dummy mínima *(último recurso)* | ✅ Sí | Activar **Abrir cajón via impresión dummy** |

El módulo prueba cada estrategia en orden y se detiene en la primera que tenga
éxito.  **Las estrategias P1–P3 no generan ningún trabajo de impresión.**

---

## Configuración recomendada (P2 — ESC/POS directo)

### Impresoras de red (TCP)

1. Ve a **Punto de Venta → Configuración → TPV** y abre tu configuración.
2. En la sección **Cajón portamonedas** introduce la dirección de la impresora:

```
192.168.1.50:9100
```

3. (Opcional) Personaliza los **Bytes del comando ESC/POS** si tu impresora
   usa un pin o temporización diferente (p. ej. `27 112 1 25 250` para pin 5).
4. Guarda y prueba el botón **🔓 Abrir cajón** en el TPV.

### Impresoras USB en Linux

```
/dev/usb/lp0
```

Si aparece error de permisos:

```bash
sudo chmod 666 /dev/usb/lp0
# o permanentemente:
sudo usermod -aG lp $USER
```

### Impresoras CUPS

```
EPSON_TM_T20
```

### Windows (proxy local)

En Windows el navegador no puede acceder directamente a la impresora USB.
Usa el proxy incluido en `tools/cash_drawer_proxy.py`:

```bash
pip install pywin32
python tools/cash_drawer_proxy.py --printer "EPSON TM-T20"
```

El proxy escucha en `http://localhost:7070` y recibe la llamada del servidor
Odoo para reenviarla vía `win32print` en modo RAW.

Instalación automática como servicio de inicio:

```bat
tools\install_proxy_windows.bat
```

---

## Configuración de impresiones dummy (P4 — último recurso)

Si ninguna de las estrategias P1–P3 está disponible, puedes activar la
impresión dummy en **Ajustes del TPV → Cajón portamonedas**:

* **Abrir cajón via impresión dummy** → activa el botón en el TPV.
* **Texto de la impresión dummy** → contenido mínimo del ticket (por defecto `.`).
* **Usar impresión web como alternativa** → usa la API Web Print del navegador.

---

## Bytes del comando ESC/POS

| Bytes (decimal) | Comando | Descripción |
|-----------------|---------|-------------|
| `27 112 0 25 250` | ESC p, pin 2 | Estándar para la mayoría de impresoras |
| `27 112 1 25 250` | ESC p, pin 5 | Pin alternativo |
| `7`             | BEL     | Algunos modelos Star Micronics |
| `27 105`        | ESC i   | Algunas impresoras antiguas |

---

## Docker

Monta el dispositivo USB en el contenedor de Odoo:

```yaml
services:
  odoo:
    devices:
      - /dev/usb/lp0:/dev/usb/lp0
    networks:
      default:
      public:    # para impresoras de red
```

---

## Solución de problemas

| Problema | Solución |
|----------|----------|
| No detecta USB | `ls /dev/usb/lp*` |
| Sin permisos en Linux | `sudo chmod 666 /dev/usb/lp0` |
| Timeout en red | `nc -zv 192.168.1.50 9100` |
| Windows — cajón no abre | Comprueba que el proxy está corriendo: `http://localhost:7070/status` |
| P3 (IoT Box) no abre | Verifica que `iface_cashdrawer` está activo en la config del TPV |

---

## Autor

**Xtendoo** — <https://xtendoo.es>

## Licencia

LGPL-3

