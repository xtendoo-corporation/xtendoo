/** @odoo-module **/
/**
 * SerialScaleService - Servicio para gestionar balanza por Web Serial API
 *
 * Este servicio gestiona la conexión con una balanza por puerto serie usando
 * la Web Serial API del navegador. Solo funciona en Chrome/Edge/Chromium con HTTPS.
 *
 * Requisitos:
 * - Chrome/Edge/Chromium
 * - HTTPS o localhost
 * - Interacción del usuario para solicitar el puerto
 */

import { registry } from "@web/core/registry";
import { Reactive } from "@web/core/utils/reactive";
import { _t } from "@web/core/l10n/translation";

// Estados de conexión
export const CONNECTION_STATUS = {
    DISCONNECTED: "disconnected",
    CONNECTING: "connecting",
    CONNECTED: "connected",
    ERROR: "error",
    NOT_SUPPORTED: "not_supported",
};

export class SerialScaleService extends Reactive {
    constructor(env, deps) {
        super();
        this.setup(env, deps);
    }

    setup(env, deps) {
        this.env = env;
        this.notification = deps.notification;

        // Estado de conexión
        this.status = CONNECTION_STATUS.DISCONNECTED;
        this.errorMessage = "";

        // Datos de la balanza
        this.lastWeight = 0;
        this.lastRawLine = "";
        this.isReading = false;

        // Objetos de Web Serial API
        this.port = null;
        this.reader = null;
        this.readableStreamClosed = null;

        // Buffer para acumular datos entrantes
        this.inputBuffer = "";

        // Configuración (se carga desde pos.config)
        this.config = {
            enabled: false,
            portHint: "COM7",
            baudRate: 9600,
            dataBits: 8,
            stopBits: 1,
            parity: "none",
            flowControl: "none",
            weightRegex: "(-?\\d+(?:[.,]\\d+)?)",
            weightUnit: "kg",
        };

        // Verificar soporte de Web Serial API
        this.isSupported = this._checkSupport();
        if (!this.isSupported) {
            this.status = CONNECTION_STATUS.NOT_SUPPORTED;
        }
    }

    /**
     * Verifica si el navegador soporta Web Serial API
     */
    _checkSupport() {
        if (typeof navigator === "undefined") {
            return false;
        }
        if (!navigator.serial) {
            console.warn("[SerialScaleService] Web Serial API no soportada en este navegador");
            return false;
        }
        // Verificar HTTPS o localhost
        const isSecure = window.isSecureContext;
        if (!isSecure) {
            console.warn("[SerialScaleService] Web Serial API requiere HTTPS o localhost");
            return false;
        }
        return true;
    }

    /**
     * Carga la configuración desde pos.config
     */
    loadConfig(posConfig) {
        if (!posConfig) return;

        this.config.enabled = posConfig.xtendoo_serial_scale_enabled || false;
        this.config.portHint = posConfig.xtendoo_serial_port_hint || "COM7";
        this.config.baudRate = posConfig.xtendoo_serial_baudrate || 9600;
        this.config.dataBits = parseInt(posConfig.xtendoo_serial_databits || "8", 10);
        this.config.stopBits = parseInt(posConfig.xtendoo_serial_stopbits || "1", 10);
        this.config.parity = posConfig.xtendoo_serial_parity || "none";
        this.config.flowControl = posConfig.xtendoo_serial_flowcontrol || "none";
        this.config.weightRegex = posConfig.xtendoo_serial_weight_regex || "(-?\\d+(?:[.,]\\d+)?)";
        this.config.weightUnit = posConfig.xtendoo_serial_weight_unit || "kg";

        console.log("[SerialScaleService] Configuración cargada:", this.config);
    }

    /**
     * Solicita al usuario seleccionar un puerto serie y conecta
     * Debe ser llamado desde un evento de usuario (click)
     */
    async connect() {
        if (!this.isSupported) {
            this.status = CONNECTION_STATUS.NOT_SUPPORTED;
            this.errorMessage = _t("Web Serial API no soportada en este navegador. Use Chrome/Edge con HTTPS.");
            return false;
        }

        if (this.status === CONNECTION_STATUS.CONNECTED) {
            console.log("[SerialScaleService] Ya conectado");
            return true;
        }

        try {
            this.status = CONNECTION_STATUS.CONNECTING;
            this.errorMessage = "";

            // Solicitar puerto al usuario (abre diálogo del navegador)
            console.log("[SerialScaleService] Solicitando puerto al usuario...");
            this.port = await navigator.serial.requestPort();

            // Configurar opciones de apertura
            const openOptions = {
                baudRate: this.config.baudRate,
                dataBits: this.config.dataBits,
                stopBits: this.config.stopBits,
                parity: this.config.parity,
                flowControl: this.config.flowControl,
            };

            console.log("[SerialScaleService] Abriendo puerto con opciones:", openOptions);
            await this.port.open(openOptions);

            this.status = CONNECTION_STATUS.CONNECTED;
            console.log("[SerialScaleService] Conectado exitosamente");

            // Iniciar lectura continua
            this._startReading();

            this.notification.add(_t("Balanza conectada correctamente"), {
                type: "success",
            });

            return true;

        } catch (error) {
            console.error("[SerialScaleService] Error al conectar:", error);
            this.status = CONNECTION_STATUS.ERROR;

            if (error.name === "NotFoundError") {
                this.errorMessage = _t("No se seleccionó ningún puerto");
            } else if (error.name === "SecurityError") {
                this.errorMessage = _t("Permiso denegado para acceder al puerto");
            } else if (error.name === "NetworkError") {
                this.errorMessage = _t("El puerto está ocupado por otra aplicación");
            } else if (error.name === "InvalidStateError") {
                this.errorMessage = _t("El puerto ya está abierto");
            } else {
                this.errorMessage = error.message || _t("Error desconocido al conectar");
            }

            this.notification.add(this.errorMessage, {
                type: "danger",
            });

            return false;
        }
    }

    /**
     * Desconecta del puerto serie
     */
    async disconnect() {
        console.log("[SerialScaleService] Desconectando...");

        try {
            this.isReading = false;

            // Cancelar el reader si existe
            if (this.reader) {
                try {
                    await this.reader.cancel();
                    this.reader.releaseLock();
                } catch (e) {
                    console.warn("[SerialScaleService] Error cancelando reader:", e);
                }
                this.reader = null;
            }

            // Esperar a que el stream se cierre
            if (this.readableStreamClosed) {
                try {
                    await this.readableStreamClosed;
                } catch (e) {
                    // Ignorar errores de cancelación
                }
                this.readableStreamClosed = null;
            }

            // Cerrar el puerto
            if (this.port) {
                try {
                    await this.port.close();
                } catch (e) {
                    console.warn("[SerialScaleService] Error cerrando puerto:", e);
                }
                this.port = null;
            }

            this.status = CONNECTION_STATUS.DISCONNECTED;
            this.inputBuffer = "";
            console.log("[SerialScaleService] Desconectado");

            this.notification.add(_t("Balanza desconectada"), {
                type: "info",
            });

            return true;

        } catch (error) {
            console.error("[SerialScaleService] Error al desconectar:", error);
            this.status = CONNECTION_STATUS.ERROR;
            this.errorMessage = error.message;
            return false;
        }
    }

    /**
     * Inicia la lectura continua del puerto serie
     */
    async _startReading() {
        if (!this.port || !this.port.readable) {
            console.error("[SerialScaleService] Puerto no disponible para lectura");
            return;
        }

        this.isReading = true;
        const decoder = new TextDecoderStream();
        this.readableStreamClosed = this.port.readable.pipeTo(decoder.writable);
        this.reader = decoder.readable.getReader();

        console.log("%c╔══════════════════════════════════════════════════════════════╗", "color: #00ff00; font-weight: bold; font-size: 14px");
        console.log("%c║  🚀 BALANZA CONECTADA - INICIANDO LECTURA CONTINUA          ║", "color: #00ff00; font-weight: bold; font-size: 14px");
        console.log("%c╚══════════════════════════════════════════════════════════════╝", "color: #00ff00; font-weight: bold; font-size: 14px");
        console.log("%c⚙️  Configuración activa:", "color: #00ffff; font-weight: bold");
        console.log("%c   • Baud Rate:", "color: #00ffff", this.config.baudRate);
        console.log("%c   • Data Bits:", "color: #00ffff", this.config.dataBits);
        console.log("%c   • Stop Bits:", "color: #00ffff", this.config.stopBits);
        console.log("%c   • Parity:", "color: #00ffff", this.config.parity);
        console.log("%c   • Regex:", "color: #00ffff", this.config.weightRegex);
        console.log("%c   • Unidad:", "color: #00ffff", this.config.weightUnit);
        console.log("%c", ""); // Línea en blanco
        console.log("%c👀 Esperando datos de la balanza...", "color: #ffff00; font-weight: bold; font-size: 13px");
        console.log("%c   (Coloca un peso en la balanza para ver los datos)", "color: #ffff00; font-style: italic");
        console.log("%c", ""); // Línea en blanco

        let readCount = 0; // Contador de lecturas

        try {
            while (this.isReading) {
                readCount++;
                console.log(`%c📥 LECTURA #${readCount} - Esperando datos del puerto serie...`, "color: #9966ff; font-weight: bold");

                const { value, done } = await this.reader.read();

                // LOG DETALLADO: Ver qué devuelve reader.read()
                console.log("%c▼▼▼ READER.READ() DEVOLVIÓ:", "color: #ff6600; font-weight: bold; font-size: 13px");
                console.log("%c   • done:", "color: #ff6600; font-weight: bold", done, `(${typeof done})`);
                console.log("%c   • value:", "color: #ff6600; font-weight: bold", value, `(${typeof value})`);
                if (value) {
                    console.log("%c   • value.length:", "color: #ff6600; font-weight: bold", value.length, "caracteres");
                    console.log("%c   • value (preview):", "color: #ff6600; font-weight: bold",
                        value.length > 100 ? value.substring(0, 100) + "..." : value);
                }
                console.log("%c▲▲▲", "color: #ff6600; font-weight: bold");

                if (done) {
                    console.log("[SerialScaleService] Stream cerrado por el dispositivo");
                    break;
                }

                if (value) {
                    this._processIncomingData(value);
                }
            }
        } catch (error) {
            if (this.isReading) {
                console.error("[SerialScaleService] Error leyendo datos:", error);
                this.status = CONNECTION_STATUS.ERROR;
                this.errorMessage = _t("Error leyendo datos de la balanza");
            }
        } finally {
            if (this.reader) {
                try {
                    this.reader.releaseLock();
                } catch (e) {
                    // Ignorar
                }
            }
        }
    }

    /**
     * Procesa los datos entrantes del puerto serie
     */
    _processIncomingData(data) {
        // LOG DESTACADO: Datos RAW recibidos
        console.log("%c━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "color: #00ff00; font-weight: bold");
        console.log("%c🎯 DATOS RECIBIDOS DE LA BALANZA", "color: #00ff00; font-weight: bold; font-size: 14px");
        console.log("%c━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "color: #00ff00; font-weight: bold");
        console.log("%cDatos RAW (string):", "color: #ffff00; font-weight: bold", data);
        console.log("%cDatos RAW (JSON):", "color: #ffff00; font-weight: bold", JSON.stringify(data));
        console.log("%cLongitud:", "color: #ffff00; font-weight: bold", data.length, "caracteres");
        console.log("%cBytes (hex):", "color: #ffff00; font-weight: bold",
            Array.from(data).map(c => c.charCodeAt(0).toString(16).padStart(2, '0')).join(' '));
        console.log("%cBytes (decimal):", "color: #ffff00; font-weight: bold",
            Array.from(data).map(c => c.charCodeAt(0)).join(' '));

        // Agregar datos al buffer
        this.inputBuffer += data;

        // Buscar líneas completas (terminadas en \n o \r\n)
        const lines = this.inputBuffer.split(/\r?\n/);

        // La última parte puede estar incompleta, la guardamos
        this.inputBuffer = lines.pop() || "";

        // LOG: Mostrar cuántas líneas se encontraron
        if (lines.length > 0) {
            console.log("%c📋 Líneas completas encontradas:", "color: #00ffff; font-weight: bold", lines.length);
            lines.forEach((line, index) => {
                if (line) {
                    console.log(`%c  Línea ${index + 1}:`, "color: #00ffff", `"${line}"`);
                }
            });
        } else {
            console.log("%c⏳ Buffer acumulando datos (esperando salto de línea)...", "color: #ff9900; font-style: italic");
            console.log("%c  Buffer actual:", "color: #ff9900", `"${this.inputBuffer}"`);
        }

        // Procesar cada línea completa
        for (const line of lines) {
            if (line.trim()) {
                this._processLine(line.trim());
            }
        }
    }

    /**
     * Procesa una línea completa de la balanza
     */
    _processLine(line) {
        console.log("%c╔════════════════════════════════════════════════════════╗", "color: #ff00ff; font-weight: bold");
        console.log("%c║  PROCESANDO LÍNEA DE LA BALANZA                       ║", "color: #ff00ff; font-weight: bold");
        console.log("%c╚════════════════════════════════════════════════════════╝", "color: #ff00ff; font-weight: bold");
        console.log("%c📝 Línea recibida:", "color: #ff00ff; font-weight: bold; font-size: 13px", `"${line}"`);
        console.log("%c📏 Longitud:", "color: #ff00ff; font-weight: bold", line.length, "caracteres");
        console.log("%c🔢 Bytes (hex):", "color: #ff00ff; font-weight: bold",
            Array.from(line).map(c => c.charCodeAt(0).toString(16).padStart(2, '0')).join(' '));
        console.log("%c🔤 Caracteres:", "color: #ff00ff; font-weight: bold",
            Array.from(line).map(c => `'${c}'`).join(' '));

        this.lastRawLine = line;

        try {
            // Aplicar regex para extraer el peso
            console.log("%c🎯 Regex configurada:", "color: #00ffff; font-weight: bold", this.config.weightRegex);
            const regex = new RegExp(this.config.weightRegex);
            const match = line.match(regex);

            console.log("%c🔍 Resultado del match:", "color: #00ffff; font-weight: bold", match);

            if (match && match[1]) {
                console.log("%c✅ MATCH ENCONTRADO!", "color: #00ff00; font-weight: bold; font-size: 14px");

                // Convertir coma a punto para parseFloat
                const weightStr = match[1].replace(",", ".");
                let weight = parseFloat(weightStr);

                console.log("%c  ➜ String extraído:", "color: #00ff00; font-weight: bold", `"${match[1]}"`);
                console.log("%c  ➜ String normalizado:", "color: #00ff00; font-weight: bold", `"${weightStr}"`);
                console.log("%c  ➜ Peso parseado (raw):", "color: #00ff00; font-weight: bold", weight);
                console.log("%c  ➜ Unidad configurada:", "color: #00ff00; font-weight: bold", this.config.weightUnit);

                if (!isNaN(weight)) {
                    // Convertir a kg si es necesario
                    if (this.config.weightUnit === "g") {
                        const originalWeight = weight;
                        weight = weight / 1000;
                        console.log("%c  ➜ Conversión:", "color: #00ff00; font-weight: bold",
                            `${originalWeight} gramos → ${weight} kg`);
                    } else if (this.config.weightUnit === "lb") {
                        const originalWeight = weight;
                        weight = weight * 0.453592;
                        console.log("%c  ➜ Conversión:", "color: #00ff00; font-weight: bold",
                            `${originalWeight} libras → ${weight} kg`);
                    }

                    this.lastWeight = weight;
                    console.log("%c┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓", "color: #00ff00; font-weight: bold; font-size: 16px");
                    console.log("%c┃  ✓ PESO ACTUALIZADO:", "color: #00ff00; font-weight: bold; font-size: 16px", weight, "kg", "┃");
                    console.log("%c┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛", "color: #00ff00; font-weight: bold; font-size: 16px");
                } else {
                    console.log("%c❌ ERROR: No se pudo parsear el peso", "color: #ff0000; font-weight: bold; font-size: 14px");
                    console.log("%c  ➜ String extraído:", "color: #ff0000; font-weight: bold", match[1]);
                    console.log("%c  ➜ Resultado de parseFloat:", "color: #ff0000; font-weight: bold", weight);
                }
            } else {
                console.log("%c❌ NO SE ENCONTRÓ PESO EN LA LÍNEA", "color: #ff0000; font-weight: bold; font-size: 14px");
                console.log("%c━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "color: #ff0000; font-weight: bold");
                console.log("%c🔧 SUGERENCIAS PARA SOLUCIONAR:", "color: #ffff00; font-weight: bold; font-size: 13px");
                console.log("%c  1️⃣  Verifica que la regex sea correcta para tu balanza", "color: #ffff00");
                console.log("%c  2️⃣  Formato actual de la línea:", "color: #ffff00", `"${line}"`);
                console.log("%c  3️⃣  Regex actual:", "color: #ffff00", this.config.weightRegex);

                // Intentar extraer cualquier número como ayuda
                const anyNumber = line.match(/(\d+[.,]?\d*)/);
                if (anyNumber) {
                    console.log("%c  4️⃣  Se encontró este número en la línea:", "color: #ffff00; font-weight: bold",
                        `"${anyNumber[1]}"`);
                    console.log("%c     💡 ¿Es este el peso? Prueba esta regex:", "color: #00ff00; font-weight: bold",
                        `(${anyNumber[1].replace(/\d/g, '\\d').replace('.', '[.,]')})`);
                    console.log("%c     💡 O esta más genérica:", "color: #00ff00; font-weight: bold",
                        `(\\d+[.,]?\\d*)`);
                }

                // Sugerencias de regex según el formato detectado
                console.log("%c  5️⃣  EJEMPLOS DE REGEX COMUNES:", "color: #00ffff; font-weight: bold");
                console.log("%c     • Para '12.345':", "color: #00ffff", "(\\d+[.,]\\d+)");
                console.log("%c     • Para 'W: 12.345':", "color: #00ffff", "W:\\s*(\\d+[.,]\\d+)");
                console.log("%c     • Para 'ST,GS, 12.345 kg':", "color: #00ffff", "(\\d+[.,]\\d+)");
                console.log("%c     • Para 'NET 12,345':", "color: #00ffff", "NET\\s+(\\d+,\\d+)");
                console.log("%c━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "color: #ff0000; font-weight: bold");
            }
        } catch (error) {
            console.log("%c💥 ERROR PROCESANDO LÍNEA:", "color: #ff0000; font-weight: bold; font-size: 14px", error);
            console.error(error);
        }
    }

    /**
     * Obtiene el peso actual
     */
    getWeight() {
        return this.lastWeight;
    }

    /**
     * Obtiene la última línea raw recibida
     */
    getRawLine() {
        return this.lastRawLine;
    }

    /**
     * Obtiene el texto del estado para mostrar en UI
     */
    getStatusText() {
        switch (this.status) {
            case CONNECTION_STATUS.CONNECTED:
                return _t("Conectado");
            case CONNECTION_STATUS.CONNECTING:
                return _t("Conectando...");
            case CONNECTION_STATUS.DISCONNECTED:
                return _t("Desconectado");
            case CONNECTION_STATUS.ERROR:
                return _t("Error");
            case CONNECTION_STATUS.NOT_SUPPORTED:
                return _t("No compatible");
            default:
                return _t("Desconocido");
        }
    }

    /**
     * Obtiene el color del estado
     */
    getStatusColor() {
        switch (this.status) {
            case CONNECTION_STATUS.CONNECTED:
                return "success";
            case CONNECTION_STATUS.CONNECTING:
                return "warning";
            case CONNECTION_STATUS.DISCONNECTED:
                return "secondary";
            case CONNECTION_STATUS.ERROR:
            case CONNECTION_STATUS.NOT_SUPPORTED:
                return "danger";
            default:
                return "secondary";
        }
    }

    /**
     * Verifica si está conectado
     */
    isConnected() {
        return this.status === CONNECTION_STATUS.CONNECTED;
    }
}

// Registrar el servicio
export const serialScaleService = {
    dependencies: ["notification"],
    start(env, deps) {
        return new SerialScaleService(env, deps);
    },
};

registry.category("services").add("serial_scale", serialScaleService);

