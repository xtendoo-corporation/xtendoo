/** @odoo-module **/
/**
 * WebUSB Printer - Apertura experimental de cajón via WebUSB API
 *
 * Permite enviar comandos ESC/POS directamente a impresoras USB conectadas
 * al PC del usuario, sin necesidad de drivers ni IoT Box.
 *
 * REQUISITOS:
 *  - Navegador Chrome/Edge/Chromium (WebUSB no disponible en Firefox/Safari)
 *  - Contexto seguro: HTTPS o localhost
 *  - Linux: puede necesitar desactivar el driver usblp (ver setup_webusb_udev.sh)
 *  - Windows: puede requerir cambio de driver con Zadig (WinUSB)
 *
 * VENDORS soportados:
 *  - Epson:    0x04B8  →  ESC p (27 112 0 25 250)
 *  - Star:     0x0519  →  BEL   (7)
 *  - Citizen:  0x1D90  →  ESC p (27 112 0 25 250)
 *  - Bixolon:  0x1504  →  ESC p (27 112 0 25 250)
 *  - Custom:   0x0DD4  →  ESC p (27 112 0 25 250)
 */

const ESCPOS_OPEN_DRAWER = new Uint8Array([0x1B, 0x70, 0x00, 0x19, 0xFA]);
const STAR_OPEN_DRAWER   = new Uint8Array([0x07]);

export const PRINTER_VENDORS = [
    { vendorId: 0x04B8, name: "Epson",    command: ESCPOS_OPEN_DRAWER },
    { vendorId: 0x0519, name: "Star",     command: STAR_OPEN_DRAWER   },
    { vendorId: 0x1D90, name: "Citizen",  command: ESCPOS_OPEN_DRAWER },
    { vendorId: 0x1504, name: "Bixolon",  command: ESCPOS_OPEN_DRAWER },
    { vendorId: 0x0DD4, name: "Custom",   command: ESCPOS_OPEN_DRAWER },
];

const STORAGE_KEY = "cash_drawer_webusb_device";

export class WebUSBPrinter {
    /**
     * Comprueba si el navegador soporta WebUSB.
     */
    static isSupported() {
        return (
            typeof navigator !== "undefined" &&
            "usb" in navigator &&
            typeof navigator.usb.requestDevice === "function"
        );
    }

    /**
     * Solicita al usuario que seleccione una impresora USB.
     * Requiere gesto de usuario (click). Guarda el vendor/product ID
     * en localStorage para reutilizarlo sin volver a pedir permiso.
     *
     * @returns {USBDevice}
     */
    async requestDevice() {
        if (!WebUSBPrinter.isSupported()) {
            throw new Error(
                "WebUSB no está disponible. Usa Chrome/Edge en HTTPS o localhost."
            );
        }
        const filters = PRINTER_VENDORS.map((v) => ({ vendorId: v.vendorId }));
        const device = await navigator.usb.requestDevice({ filters });
        localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({ vendorId: device.vendorId, productId: device.productId })
        );
        return device;
    }

    /**
     * Recupera el dispositivo guardado previamente (sin diálogo al usuario).
     *
     * @returns {USBDevice|null}
     */
    async getSavedDevice() {
        if (!WebUSBPrinter.isSupported()) {
            return null;
        }
        const saved = localStorage.getItem(STORAGE_KEY);
        if (!saved) {
            return null;
        }
        try {
            const { vendorId, productId } = JSON.parse(saved);
            const devices = await navigator.usb.getDevices();
            return (
                devices.find(
                    (d) => d.vendorId === vendorId && d.productId === productId
                ) || null
            );
        } catch {
            return null;
        }
    }

    /**
     * Abre el cajón portamonedas via WebUSB.
     *
     * @param {Uint8Array|null} customCommand  Bytes del comando (opcional).
     *     Si no se especifica, se usa el comando del vendor o ESC p por defecto.
     * @throws {Error} si no hay dispositivo guardado, o falla la comunicación.
     */
    async openCashbox(customCommand = null) {
        if (!WebUSBPrinter.isSupported()) {
            throw new Error(
                "WebUSB no está disponible en este navegador."
            );
        }

        const device = await this.getSavedDevice();
        if (!device) {
            throw new Error(
                "No hay ninguna impresora USB guardada. " +
                "Usa el botón 'Vincular impresora USB' primero."
            );
        }

        // Determinar el comando a enviar
        const vendorInfo = PRINTER_VENDORS.find(
            (v) => v.vendorId === device.vendorId
        );
        const command =
            customCommand ||
            (vendorInfo ? vendorInfo.command : ESCPOS_OPEN_DRAWER);

        // Abrir dispositivo
        await device.open();

        try {
            if (device.configuration === null) {
                await device.selectConfiguration(1);
            }

            // Buscar el endpoint Bulk OUT
            let endpoint = null;
            let interfaceNumber = null;

            for (const iface of device.configuration.interfaces) {
                for (const alt of iface.alternates) {
                    for (const ep of alt.endpoints) {
                        if (ep.direction === "out" && ep.type === "bulk") {
                            endpoint = ep;
                            interfaceNumber = iface.interfaceNumber;
                            break;
                        }
                    }
                    if (endpoint) break;
                }
                if (endpoint) break;
            }

            if (!endpoint) {
                throw new Error(
                    "No se encontró ningún endpoint Bulk OUT en la impresora USB. " +
                    "El dispositivo puede no ser compatible con WebUSB."
                );
            }

            await device.claimInterface(interfaceNumber);

            try {
                const result = await device.transferOut(
                    endpoint.endpointNumber,
                    command
                );
                if (result.status !== "ok") {
                    throw new Error(
                        "Error en la transferencia USB: status = " + result.status
                    );
                }
            } finally {
                await device.releaseInterface(interfaceNumber);
            }
        } finally {
            await device.close();
        }
    }

    /**
     * Elimina el dispositivo guardado en localStorage.
     */
    clearSavedDevice() {
        localStorage.removeItem(STORAGE_KEY);
    }
}

