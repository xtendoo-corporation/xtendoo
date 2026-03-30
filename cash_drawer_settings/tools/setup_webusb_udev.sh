#!/bin/bash
# =============================================================================
# setup_webusb_udev.sh — Configura udev para permitir WebUSB en Linux
# =============================================================================
# En Linux, el kernel captura automáticamente los dispositivos USB de impresora
# con el driver "usblp". Esto impide que el navegador acceda al dispositivo via
# WebUSB. Este script crea una regla udev que:
#   1. Desvincula el driver usblp cuando se conecta la impresora
#   2. Otorga permisos de lectura/escritura al grupo "plugdev"
#
# Uso:
#   sudo bash setup_webusb_udev.sh
#
# Fabricantes soportados (añade más según necesites):
#   Epson:    0x04b8
#   Star:     0x0519
#   Citizen:  0x1d90
#   Bixolon:  0x1504
#   Custom:   0x0dd4
# =============================================================================

set -e

RULES_FILE="/etc/udev/rules.d/99-webusb-printer.rules"

echo ""
echo "======================================================"
echo "  Configuración WebUSB para impresoras de ticket"
echo "======================================================"
echo ""

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] Este script debe ejecutarse como root (sudo)."
    exit 1
fi

# Añadir usuario actual al grupo plugdev si no está ya
CURRENT_USER="${SUDO_USER:-$(who am i | awk '{print $1}')}"
if [ -n "$CURRENT_USER" ] && ! groups "$CURRENT_USER" | grep -q plugdev; then
    echo "[INFO] Añadiendo $CURRENT_USER al grupo plugdev..."
    usermod -aG plugdev "$CURRENT_USER"
    echo "[OK] Usuario $CURRENT_USER añadido a plugdev."
    echo "     (Cierra sesión y vuelve a entrar para que surta efecto)"
fi

echo "[INFO] Creando regla udev en $RULES_FILE..."

cat > "$RULES_FILE" << 'EOF'
# Reglas udev para WebUSB con impresoras de ticket ESC/POS
# Generado por setup_webusb_udev.sh (cash_drawer_settings)
#
# Para cada impresora:
#   1. ATTR{idVendor} y ATTR{idProduct} identifican el dispositivo
#   2. RUN+="..." desvincula el driver usblp para liberar el dispositivo
#   3. MODE="0664" y GROUP="plugdev" otorgan permisos al usuario del navegador

# Epson (vendorId=0x04b8)
SUBSYSTEM=="usb", ATTR{idVendor}=="04b8", MODE="0664", GROUP="plugdev", \
    RUN+="/bin/sh -c 'echo -n $kernel > /sys/bus/usb/drivers/usblp/unbind 2>/dev/null || true'"

# Star Micronics (vendorId=0x0519)
SUBSYSTEM=="usb", ATTR{idVendor}=="0519", MODE="0664", GROUP="plugdev", \
    RUN+="/bin/sh -c 'echo -n $kernel > /sys/bus/usb/drivers/usblp/unbind 2>/dev/null || true'"

# Citizen (vendorId=0x1d90)
SUBSYSTEM=="usb", ATTR{idVendor}=="1d90", MODE="0664", GROUP="plugdev", \
    RUN+="/bin/sh -c 'echo -n $kernel > /sys/bus/usb/drivers/usblp/unbind 2>/dev/null || true'"

# Bixolon (vendorId=0x1504)
SUBSYSTEM=="usb", ATTR{idVendor}=="1504", MODE="0664", GROUP="plugdev", \
    RUN+="/bin/sh -c 'echo -n $kernel > /sys/bus/usb/drivers/usblp/unbind 2>/dev/null || true'"

# Custom (vendorId=0x0dd4)
SUBSYSTEM=="usb", ATTR{idVendor}=="0dd4", MODE="0664", GROUP="plugdev", \
    RUN+="/bin/sh -c 'echo -n $kernel > /sys/bus/usb/drivers/usblp/unbind 2>/dev/null || true'"
EOF

echo "[OK] Regla udev creada."

# Recargar udev
echo "[INFO] Recargando reglas udev..."
udevadm control --reload-rules
udevadm trigger

echo ""
echo "======================================================"
echo "  Configuración completada."
echo ""
echo "  Para verificar:"
echo "    1. Desconecta y vuelve a conectar la impresora USB"
echo "    2. Ejecuta: lsusb | grep -i epson   (o tu fabricante)"
echo "    3. En Chrome/Edge, navega al TPV y usa el botón"
echo "       'Vincular impresora USB' del menú hamburguesa"
echo ""
echo "  Si usas una impresora no listada, edita:"
echo "    $RULES_FILE"
echo "  y añade la línea con el idVendor correcto."
echo "======================================================"
echo ""

