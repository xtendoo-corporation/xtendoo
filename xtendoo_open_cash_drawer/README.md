# Xtendoo Open Cash Drawer
Módulo para abrir el cajón portamonedas desde el **Punto de Venta (TPV)** en Odoo 19.
## Características
* **🔍 Detección automática** de impresoras USB/serie/CUPS
* **🌐 TCP directo** para impresoras de red (IP:puerto)
* **⚙️ Comando ESC/POS configurable**
* **✅ Compatible** Windows + Linux + Docker
## Uso rápido
1. Ve a **Ajustes → Cajón Portamonedas**
2. Clic en **🔍 Detectar impresoras** → copia el nombre
3. Pégalo en **"Impresora configurada"**
4. Clic en **🔓 Abrir cajón portamonedas**
## Impresoras de red
Escribe directamente:
```
192.168.1.50:9100
```
## Impresoras USB
### Linux
Haz clic en **🔍 Detectar** y copia:
```
/dev/usb/lp0
```
Si aparece 🔒 sin permisos:
```bash
sudo chmod 666 /dev/usb/lp0
```
### Windows
**Opción 1** - Compartir como RAW:
1. Panel control → Dispositivos e impresoras → Propiedades → Puertos
2. Añadir TCP/IP: `IP_de_este_PC:9100`
3. En Odoo: `192.168.X.X:9100`
**Opción 2** - Odoo nativo Windows:
```
EPSON TM-T20
```
## Comando personalizado
Bytes decimales separados por espacios:
```
27 112 0 25 250    → ESC p estándar
27 105             → ESC i (default)
```
## Docker
Montar dispositivo USB:
```yaml
services:
  odoo:
    devices:
      - /dev/usb/lp0:/dev/usb/lp0
    networks:
      default:
      public:    # para impresoras red
```
## Troubleshooting
| Problema | Solución |
|----------|----------|
| No detecta USB | `ls /dev/usb/lp*` |
| Sin permisos | `sudo chmod 666 /dev/usb/lp0` |
| Red timeout | `nc -zv IP 9100` |
## Autor
**Xtendoo** - https://xtendoo.es
## Licencia
LGPL-3
