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

## Docker y doodba — despliegue en servidor cloud

Esta es la situación más habitual en producción: Odoo corre en un **servidor
cloud** dentro de un contenedor Docker (posiblemente con
[doodba](https://github.com/Tecnativa/doodba)), y la impresora de tickets
está físicamente en el local del negocio.

El diagrama de decisión depende de **dónde está conectada la impresora**:

```
¿Dónde está la impresora?
│
├─ En el mismo servidor cloud (USB conectado al VPS)
│    └─► Escenario B — monta el dispositivo en el compose
│
├─ En la misma máquina que hospeda Docker (host Docker)
│    └─► Escenario D — usa "host:9100" como dirección
│
├─ Impresora de red con IP pública/VPN accesible desde el cloud
│    └─► Escenario A — sin cambios en compose; solo config Odoo
│
└─ Impresora en la red LOCAL del cajero (caso más frecuente en cloud)
     └─► Escenario C — proxy local en el PC del cajero
```

> El archivo `tools/docker-compose.cash-drawer.yml` incluye fragmentos
> listos para copiar de cada escenario.

---

### Escenario A — Impresora de red con IP accesible desde el cloud

La impresora tiene una IP fija accesible desde el VPS (IP pública, VPN,
o red privada compartida). **No se requieren cambios en `docker-compose.yml`.**

Configura solo en Odoo:

```
TPV → Configuración → Cajón portamonedas → Dirección: 192.168.1.50:9100
```

---

### Escenario B — Impresora USB conectada al propio servidor

El VPS tiene una impresora USB conectada físicamente. Monta el dispositivo
dentro del contenedor añadiendo en `docker-compose.yml` (o `prod.yaml` de doodba):

```yaml
services:
  odoo:
    devices:
      - /dev/usb/lp0:/dev/usb/lp0   # ajusta al nodo real
```

Comprueba el nodo en el host del servidor:

```bash
ls /dev/usb/lp*
```

Configura en Odoo:

```
Dirección de la impresora: /dev/usb/lp0
```

---

### Escenario C — Servidor cloud + impresora en la red local del cajero *(caso más frecuente)*

La impresora está en el local del negocio, conectada al PC del cajero.
El contenedor Odoo en el cloud **no puede alcanzarla directamente**.

**Solución: proxy local (`cash_drawer_proxy.py`) en el PC del cajero**

1. Copia `tools/cash_drawer_proxy.py` al PC donde está conectada la impresora.
2. Instala la dependencia y lanza el proxy:

   ```bash
   pip install pywin32          # solo Windows
   python cash_drawer_proxy.py --port 7070 --printer "EPSON TM-T20"
   ```

   O en Linux:

   ```bash
   python cash_drawer_proxy.py --port 7070
   # el proxy detecta la impresora por CUPS automáticamente
   ```

3. Para que el proxy arranque automáticamente en Windows:

   ```bat
   install_proxy_windows.bat
   ```

4. El proxy escucha en `http://localhost:7070` en la máquina del cajero.
   El navegador (POS) usa la estrategia P1/P3 para comunicarse con él.

> **Nota**: No se necesitan cambios en `docker-compose.yml` del servidor
> para este escenario. El proxy corre en el PC local, no en el servidor.

---

### Escenario D — Impresora accesible desde el host Docker

El host que ejecuta Docker tiene acceso a la impresora (USB o red local)
y quieres que el servidor Odoo envíe el pulso ESC/POS desde el contenedor
hacia el host.

Usa el hostname especial **`host`** como dirección; el módulo lo resuelve
automáticamente al gateway Docker (`ip route`):

```
Dirección de la impresora: host:9100
```

Alternativamente, para que Docker exponga el host con nombre conocido
(Docker 20.10+), añade en `docker-compose.yml`:

```yaml
services:
  odoo:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Y usa `host.docker.internal:9100` como dirección en Odoo.

---

### Doodba (`prod.yaml`)

Añade el bloque correspondiente dentro de `services > odoo` en tu `prod.yaml`:

```yaml
# prod.yaml (fragmento)
version: "2.4"
services:
  odoo:
    # Escenario B: impresora USB en el servidor
    devices:
      - /dev/usb/lp0:/dev/usb/lp0

    # Escenario D: impresora en el host Docker
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

---

### Resumen rápido — ¿qué dirección pongo en Odoo?

| Situación | Dirección en Odoo |
|-----------|-------------------|
| Impresora de red (IP pública o VPN) | `192.168.1.50:9100` |
| USB en el mismo servidor | `/dev/usb/lp0` |
| CUPS en el mismo servidor | `EPSON_TM_T20` |
| Impresora en el host Docker (auto) | `host:9100` |
| Impresora en el host Docker (nombre) | `host.docker.internal:9100` |
| Red local del cajero (proxy) | — no se usa P2; se usa P1/P3 — |

---

## Solución de problemas

| Problema | Solución |
|----------|----------|
| No detecta USB | `ls /dev/usb/lp*` |
| Sin permisos en Linux | `sudo chmod 666 /dev/usb/lp0` |
| Timeout en red | `nc -zv 192.168.1.50 9100` |
| Windows — cajón no abre | Comprueba que el proxy está corriendo: `http://localhost:7070/status` |
| P3 (IoT Box) no abre | Verifica que `iface_cashdrawer` está activo en la config del TPV |
| Docker — `host:9100` no funciona | Verifica `ip route` dentro del contenedor: `docker exec odoo ip route` |
| Docker — contenedor sin `ip` | Instala `iproute2`: `apt-get install -y iproute2` en el Dockerfile |
| doodba — dispositivo no aparece | Añade `devices:` en `prod.yaml` y reinicia con `docker-compose up -d` |
| Cloud — impresora no alcanzable | Usa el proxy local (Escenario C) o una VPN entre el cajero y el servidor |


---

## Autor

**Xtendoo** — <https://xtendoo.es>

## Licencia

LGPL-3

