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

        this.config.enabled = posConfig.xtd_serial_scale_enabled || false;
        this.config.portHint = posConfig.xtd_serial_port_hint || "COM7";
        this.config.baudRate = posConfig.xtd_serial_baudrate || 9600;
        this.config.dataBits = parseInt(posConfig.xtd_serial_databits || "8", 10);
        this.config.stopBits = parseInt(posConfig.xtd_serial_stopbits || "1", 10);
        this.config.parity = posConfig.xtd_serial_parity || "none";
        this.config.flowControl = posConfig.xtd_serial_flowcontrol || "none";
        this.config.weightRegex = posConfig.xtd_serial_weight_regex || "(-?\\d+(?:[.,]\\d+)?)";

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

        console.log("[SerialScaleService] Iniciando lectura continua...");

        try {
            while (this.isReading) {
                const { value, done } = await this.reader.read();

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
        // Agregar datos al buffer
        this.inputBuffer += data;

        // Buscar líneas completas (terminadas en \n o \r\n)
        const lines = this.inputBuffer.split(/\r?\n/);

        // La última parte puede estar incompleta, la guardamos
        this.inputBuffer = lines.pop() || "";

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
        console.log("[SerialScaleService] Línea recibida:", line);
        this.lastRawLine = line;

        try {
            // Aplicar regex para extraer el peso
            const regex = new RegExp(this.config.weightRegex);
            const match = line.match(regex);

            if (match && match[1]) {
                // Convertir coma a punto para parseFloat
                const weightStr = match[1].replace(",", ".");
                const weight = parseFloat(weightStr);

                if (!isNaN(weight)) {
                    this.lastWeight = weight;
                    console.log("[SerialScaleService] Peso parseado:", weight);
                } else {
                    console.warn("[SerialScaleService] No se pudo parsear el peso:", match[1]);
                }
            } else {
                console.warn("[SerialScaleService] No se encontró peso en la línea:", line);
            }
        } catch (error) {
            console.error("[SerialScaleService] Error procesando línea:", error);
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

