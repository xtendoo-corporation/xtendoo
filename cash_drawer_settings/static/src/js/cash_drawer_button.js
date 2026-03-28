/** @odoo-module **/
/**
 * Cash Drawer Button - Patch del Navbar del TPV
 *
 * Añade el método openCashDrawer() al Navbar con una cascada de estrategias:
 *
 *   1. Hardware Proxy / IoT Box  — mecanismo nativo de Odoo (iface_cashdrawer)
 *   2. WebUSB (experimental)    — impresora USB conectada al PC del usuario
 *   3. Proxy local              — script Python en localhost:7070 (Windows)
 *   4. RPC al backend           — TCP socket/CUPS desde el servidor Odoo
 *
 * La visibilidad del botón se controla con pos.config.cash_drawer_pos_enabled.
 */

import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { WebUSBPrinter } from "@cash_drawer_settings/js/webusb_printer";
import { _t } from "@web/core/l10n/translation";

/** Instancia única del cliente WebUSB (ciclo de vida del POS) */
const _webUsb = new WebUSBPrinter();

/** Puerto del proxy local para Windows */
const LOCAL_PROXY_PORT = 7070;

patch(Navbar.prototype, {
    // ------------------------------------------------------------------
    // Getter de visibilidad
    // ------------------------------------------------------------------

    /**
     * Muestra el botón si el cajón está habilitado en la configuración del TPV.
     * @returns {boolean}
     */
    get showCashDrawerButton() {
        return Boolean(this.pos.config.cash_drawer_pos_enabled);
    },

    /**
     * Muestra el botón de vincular USB si WebUSB está soportado en el navegador.
     * @returns {boolean}
     */
    get showWebUsbButton() {
        return (
            Boolean(this.pos.config.cash_drawer_pos_enabled) &&
            WebUSBPrinter.isSupported()
        );
    },

    // ------------------------------------------------------------------
    // Apertura del cajón (cascada de estrategias)
    // ------------------------------------------------------------------

    /**
     * Intenta abrir el cajón portamonedas usando la primera estrategia
     * que tenga éxito, en orden de preferencia.
     */
    async openCashDrawer() {
        const errors = [];

        // ── Estrategia 1: Hardware Proxy / IoT Box ───────────────────
        if (this.pos.config.iface_cashdrawer && this.hardwareProxy.printer) {
            try {
                await this.hardwareProxy.openCashbox(_t("Abrir cajón"));
                this._notifyCashDrawerOk(_t("Cajón abierto (HW Proxy)"));
                return;
            } catch (err) {
                errors.push("HW Proxy: " + (err.message || String(err)));
            }
        }

        // ── Estrategia 2: WebUSB (experimental) ──────────────────────
        if (WebUSBPrinter.isSupported()) {
            // Solo intentar si hay un dispositivo previamente vinculado
            const hasSaved = Boolean(
                localStorage.getItem("cash_drawer_webusb_device")
            );
            if (hasSaved) {
                try {
                    await _webUsb.openCashbox();
                    this._notifyCashDrawerOk(_t("Cajón abierto (USB)"));
                    return;
                } catch (err) {
                    errors.push("WebUSB: " + (err.message || String(err)));
                    // Si el dispositivo no está disponible, limpiar la caché
                    if (
                        err.message &&
                        (err.message.includes("No device") ||
                            err.message.includes("not found"))
                    ) {
                        _webUsb.clearSavedDevice();
                    }
                }
            }
        }

        // ── Estrategia 3: Proxy local (Windows helper script) ────────
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000);
            try {
                const resp = await fetch(
                    `http://localhost:${LOCAL_PROXY_PORT}/open_cashbox`,
                    {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({}),
                        signal: controller.signal,
                    }
                );
                if (resp.ok) {
                    this._notifyCashDrawerOk(_t("Cajón abierto (proxy local)"));
                    return;
                }
                errors.push(`Proxy local: HTTP ${resp.status}`);
            } finally {
                clearTimeout(timeoutId);
            }
        } catch {
            // El proxy no está ejecutándose; continuar con el siguiente intento
        }

        // ── Estrategia 4: RPC al backend de Odoo ─────────────────────
        try {
            await this.pos.data.orm.call(
                "pos.config",
                "action_pos_open_cash_drawer",
                [[this.pos.config.id]]
            );
            this._notifyCashDrawerOk(_t("Cajón abierto"));
            return;
        } catch (err) {
            errors.push("RPC: " + (err.message || String(err)));
        }

        // ── Todos los intentos fallaron ───────────────────────────────
        this.notification.add(
            _t(
                "No se pudo abrir el cajón portamonedas. " +
                "Revisa la configuración en Ajustes → Cajón Portamonedas."
            ),
            { type: "danger", sticky: true }
        );
        console.error("[CashDrawer] Todos los intentos fallaron:", errors);
    },

    // ------------------------------------------------------------------
    // Vincular impresora USB (requiere gesto de usuario)
    // ------------------------------------------------------------------

    /**
     * Solicita al usuario que seleccione la impresora USB para el cajón.
     * Solo disponible si WebUSB está soportado por el navegador.
     */
    async requestWebUsbDevice() {
        try {
            await _webUsb.requestDevice();
            this.notification.add(
                _t(
                    "Impresora USB vinculada correctamente. " +
                    "Prueba ahora el botón 'Abrir cajón portamonedas'."
                ),
                { type: "success" }
            );
        } catch (err) {
            if (err.name === "NotFoundError") {
                // El usuario cerró el diálogo sin seleccionar
                return;
            }
            this.notification.add(
                _t("Error al vincular impresora USB: ") + err.message,
                { type: "danger" }
            );
        }
    },

    // ------------------------------------------------------------------
    // Helpers privados
    // ------------------------------------------------------------------

    _notifyCashDrawerOk(message) {
        this.notification.add(message, { type: "success" });
    },
});

