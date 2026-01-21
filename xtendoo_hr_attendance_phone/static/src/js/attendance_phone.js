/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
// Importar usando la exportación por defecto
import publicKiosk from "@hr_attendance/public_kiosk/public_kiosk_app";

const { kioskAttendanceApp } = publicKiosk;

console.log("[ATTENDANCE_PHONE] Módulo cargado");

// ============================================
// STORAGE MANAGER - Gestiona localStorage
// ============================================
const StorageManager = {
    setCredentials(phone, pin) {
        try {
            localStorage.setItem('attendance_phone', phone);
            localStorage.setItem('attendance_pin', pin);
            console.log("[ATTENDANCE_PHONE] ✅ Credenciales guardadas en localStorage");
        } catch (error) {
            console.warn("[ATTENDANCE_PHONE] ⚠️ Error guardando en localStorage:", error);
        }
    },

    getCredentials() {
        try {
            const phone = localStorage.getItem('attendance_phone');
            const pin = localStorage.getItem('attendance_pin');
            return { phone, pin };
        } catch (error) {
            console.warn("[ATTENDANCE_PHONE] ⚠️ Error leyendo localStorage:", error);
            return { phone: null, pin: null };
        }
    },

    clearCredentials() {
        try {
            localStorage.removeItem('attendance_phone');
            localStorage.removeItem('attendance_pin');
            console.log("[ATTENDANCE_PHONE] ✅ Credenciales borradas de localStorage");
        } catch (error) {
            console.warn("[ATTENDANCE_PHONE] ⚠️ Error limpiando localStorage:", error);
        }
    },

    hasCredentials() {
        const { phone, pin } = this.getCredentials();
        return !!(phone && pin);
    }
};

// Componente para la pantalla de asistencia por teléfono
export class KioskPhoneAttendance extends Component {
    static template = "xtendoo_hr_attendance_phone.kiosk_phone_screen";

    static props = {
        token: { type: String },
        companyId: { type: Number },
        companyName: { type: String },
        companyImageUrl: { type: String },
        onAttendanceRegistered: { type: Function, optional: true },
    };

    setup() {
        console.log("[ATTENDANCE_PHONE] Setup del componente KioskPhoneAttendance");

        this.notification = useService("notification");
        this.ui = useService("ui");

        // Recuperar credenciales guardadas
        const { phone, pin } = StorageManager.getCredentials();
        const hasStoredCredentials = StorageManager.hasCredentials();

        this.state = useState({
            isProcessing: false,
            phone: phone || "",
            pin: pin || "",
            message: "",
            messageType: "",
            // Estado del empleado (dentro/fuera)
            employeeStatus: null,
            statusMessage: "",
            statusClass: ""
        });

        console.log("[ATTENDANCE_PHONE] Componente configurado. Credenciales guardadas:", hasStoredCredentials);

        // Si hay teléfono guardado, consultar estado del empleado
        if (phone) {
            this.checkEmployeeStatus();
        }
    }

    /**
     * Consulta el estado actual del empleado (DENTRO/FUERA)
     */
    async checkEmployeeStatus() {
        const phone = this.state.phone.trim();

        if (!phone) {
            return;
        }

        console.log("[ATTENDANCE_PHONE] Consultando estado del empleado...");

        try {
            const result = await rpc('/attendance/phone/status', {
                phone: phone
            });

            if (result.success) {
                this.state.employeeStatus = result.status;
                this.state.statusMessage = result.message;
                this.state.statusClass = result.status_class;
                console.log("[ATTENDANCE_PHONE] Estado del empleado:", result.status, "-", result.message);
            } else {
                console.warn("[ATTENDANCE_PHONE] No se pudo obtener el estado:", result.error);
                // No mostrar error, simplemente no mostrar banner
                this.state.employeeStatus = null;
            }

        } catch (error) {
            console.warn("[ATTENDANCE_PHONE] Error consultando estado:", error);
            this.state.employeeStatus = null;
        }
    }

    get companyImageUrl() {
        return this.props.companyImageUrl;
    }

    /**
     * Maneja el envío del formulario principal
     */
    async onSubmit(event) {
        console.log("[ATTENDANCE_PHONE] Formulario principal enviado");
        event.preventDefault();

        const form = event.target;
        const phoneInput = form.querySelector('#main_phone_number');
        const pinInput = form.querySelector('#main_pin_code');

        if (!phoneInput || !pinInput) {
            console.error("[ATTENDANCE_PHONE] Inputs del formulario no encontrados");
            return;
        }

        const phone = phoneInput.value.trim();
        const pin = pinInput.value.trim();

        console.log("[ATTENDANCE_PHONE] Datos del formulario:", {
            phone: phone.substring(0, 3) + '***',
            pin: '***'
        });

        // Validación básica
        if (!phone || !pin) {
            console.warn("[ATTENDANCE_PHONE] Campos requeridos vacíos");
            this.showMessage(_t("Por favor complete todos los campos"), 'warning');
            return;
        }

        if (pin.length < 3) {
            console.warn("[ATTENDANCE_PHONE] PIN demasiado corto");
            this.showMessage(_t("El PIN debe tener al menos 3 caracteres"), 'warning');
            return;
        }

        // Mostrar loading
        this.state.isProcessing = true;
        this.ui.block();

        console.log("[ATTENDANCE_PHONE] Iniciando proceso de validación...");

        try {
            const result = await rpc('/attendance/phone/validate', {
                phone: phone,
                pin: pin,
                token: this.props.token
            });

            console.log("[ATTENDANCE_PHONE] Respuesta del servidor:", {
                success: result.success,
                employee_id: result.employee_id || 'N/A',
                employee_name: result.name || 'N/A',
                error: result.error || 'N/A'
            });

            if (result.success) {
                console.log("[ATTENDANCE_PHONE] ✅ Asistencia registrada exitosamente");

                // Guardar credenciales automáticamente siempre
                StorageManager.setCredentials(phone, pin);

                // Mostrar mensaje de éxito con tipo de acción (Entrada/Salida)
                const actionText = result.action_type === 'check_in' ? 'Entrada' : 'Salida';
                this.showMessage(
                    _t("%(action)s registrada para %(name)s correctamente", { action: actionText, name: result.name }),
                    'success'
                );

                // En lugar de resetear todo el formulario, solo limpiar el PIN
                pinInput.value = '';
                pinInput.focus();

                // Callback opcional
                if (this.props.onAttendanceRegistered) {
                    this.props.onAttendanceRegistered(result);
                }

                // Mantenerse en la misma pantalla; opcionalmente ocultar el mensaje tras unos segundos
                setTimeout(() => {
                    this.state.message = "";
                    // Actualizar estado del empleado después del fichaje
                    if (this.state.phone) {
                        this.checkEmployeeStatus();
                    }
                }, 3000);

            } else {
                console.warn("[ATTENDANCE_PHONE] ❌ Validación fallida:", result.error);
                this.showMessage(
                    result.error || _t("PIN o número de teléfono incorrecto"),
                    'danger'
                );

                // Limpiar PIN por seguridad
                pinInput.value = '';
                pinInput.focus();
            }

        } catch (error) {
            console.error("[ATTENDANCE_PHONE] ❌ Error en la solicitud:", error);
            this.showMessage(
                _t("Error de conexión. Verifique su conexión a internet e inténtelo nuevamente."),
                'danger'
            );
        } finally {
            this.state.isProcessing = false;
            this.ui.unblock();
            console.log("[ATTENDANCE_PHONE] Proceso de validación completado");
        }
    }

    /**
     * Envía asistencia con credenciales guardadas (sin mostrar formulario)
     */
    async quickSubmit() {
        console.log("[ATTENDANCE_PHONE] Envío rápido con credenciales guardadas");
        const phone = this.state.phone.trim();
        const pin = this.state.pin.trim();

        this.state.isProcessing = true;
        this.ui.block();

        try {
            const result = await rpc('/attendance/phone/validate', {
                phone: phone,
                pin: pin,
                token: this.props.token
            });

            if (result.success) {
                const actionText = result.action_type === 'check_in' ? 'Entrada' : 'Salida';
                this.showMessage(
                    _t("%(action)s registrada para %(name)s correctamente", { action: actionText, name: result.name }),
                    'success'
                );

                if (this.props.onAttendanceRegistered) {
                    this.props.onAttendanceRegistered(result);
                }

                // Permanecer en la misma pantalla; ocultar mensaje tras breve tiempo
                setTimeout(() => {
                    this.state.message = "";
                    // Actualizar estado del empleado después del fichaje
                    this.checkEmployeeStatus();
                }, 2000);

            } else {
                this.showMessage(_t("Credenciales inválidas. Por favor ingrese nuevamente."), 'danger');
                StorageManager.clearCredentials();
            }

        } catch (error) {
            console.error("[ATTENDANCE_PHONE] Error:", error);
            this.showMessage(_t("Error de conexión"), 'danger');
        } finally {
            this.state.isProcessing = false;
            this.ui.unblock();
        }
    }


    /**
     * Muestra un mensaje en el componente
     */
    showMessage(message, type = 'info') {
        console.log("[ATTENDANCE_PHONE] Mostrando mensaje:", { message, type });
        this.state.message = message;
        this.state.messageType = type;

        // También intentar mostrar notificación
        try {
            if (this.notification && typeof this.notification.add === 'function') {
                this.notification.add(message, {
                    type: type,
                    sticky: type !== 'success'
                });
            }
        } catch (error) {
            console.warn("[ATTENDANCE_PHONE] No se pudo mostrar notificación:", error);
        }
    }
}

// Componente para la pantalla de asistencia SOLO por teléfono (sin PIN)
export class KioskPhoneOnlyAttendance extends Component {
    static template = "xtendoo_hr_attendance_phone.kiosk_phone_only_screen";

    static props = {
        token: { type: String },
        companyId: { type: Number },
        companyName: { type: String },
        companyImageUrl: { type: String },
        onAttendanceRegistered: { type: Function, optional: true },
    };

    setup() {
        console.log("[ATTENDANCE_PHONE_ONLY] Setup del componente KioskPhoneOnlyAttendance");

        this.notification = useService("notification");
        this.ui = useService("ui");

        const { phone } = StorageManager.getCredentials();
        const hasStoredPhone = !!phone;

        this.state = useState({
            isProcessing: false,
            phone: phone || "",
            message: "",
            messageType: "",
            // Estado del empleado (dentro/fuera)
            employeeStatus: null,
            statusMessage: "",
            statusClass: ""
        });

        console.log("[ATTENDANCE_PHONE_ONLY] Componente configurado. Teléfono guardado:", hasStoredPhone);

        // Si hay teléfono guardado, consultar estado del empleado
        if (phone) {
            this.checkEmployeeStatus();
        }
    }

    /**
     * Consulta el estado actual del empleado (DENTRO/FUERA)
     */
    async checkEmployeeStatus() {
        const phone = this.state.phone.trim();

        if (!phone) {
            return;
        }

        console.log("[ATTENDANCE_PHONE_ONLY] Consultando estado del empleado...");

        try {
            const result = await rpc('/attendance/phone/status', {
                phone: phone
            });

            if (result.success) {
                this.state.employeeStatus = result.status;
                this.state.statusMessage = result.message;
                this.state.statusClass = result.status_class;
                console.log("[ATTENDANCE_PHONE_ONLY] Estado del empleado:", result.status, "-", result.message);
            } else {
                console.warn("[ATTENDANCE_PHONE_ONLY] No se pudo obtener el estado:", result.error);
                this.state.employeeStatus = null;
            }

        } catch (error) {
            console.warn("[ATTENDANCE_PHONE_ONLY] Error consultando estado:", error);
            this.state.employeeStatus = null;
        }
    }

    get companyImageUrl() {
        return this.props.companyImageUrl;
    }

    async onSubmit(event) {
        console.log("[ATTENDANCE_PHONE_ONLY] Formulario enviado");
        event.preventDefault();

        const form = event.target;
        const phoneInput = form.querySelector('#phone_only_number');

        if (!phoneInput) {
            console.error("[ATTENDANCE_PHONE_ONLY] Input no encontrado");
            return;
        }

        const phone = phoneInput.value.trim();

        if (!phone) {
            this.showMessage(_t("Por favor ingrese su número de teléfono"), 'warning');
            return;
        }

        this.state.isProcessing = true;
        this.ui.block();

        try {
            const result = await rpc('/attendance/phone/validate_phone_only', {
                phone: phone,
                token: this.props.token
            });

            if (result.success) {
                console.log("[ATTENDANCE_PHONE_ONLY] ✅ Asistencia registrada");

                // Guardar teléfono automáticamente siempre
                StorageManager.setCredentials(phone, 'phone_only');

                const actionText = result.action_type === 'check_in' ? 'Entrada' : 'Salida';
                this.showMessage(
                    _t("%(action)s registrada para %(name)s correctamente", { action: actionText, name: result.name }),
                    'success'
                );

                if (this.props.onAttendanceRegistered) {
                    this.props.onAttendanceRegistered(result);
                }

                // Mantenerse en la misma pantalla; opcionalmente borrar el campo y ocultar mensaje
                // phoneInput.value = '';
                setTimeout(() => {
                    this.state.message = "";
                    // Actualizar estado del empleado después del fichaje
                    if (this.state.phone) {
                        this.checkEmployeeStatus();
                    }
                }, 3000);

            } else {
                console.warn("[ATTENDANCE_PHONE_ONLY] ❌ Validación fallida:", result.error);
                this.showMessage(result.error || _t("Teléfono no reconocido"), 'danger');
                phoneInput.focus();
            }

        } catch (error) {
            console.error("[ATTENDANCE_PHONE_ONLY] Error:", error);
            this.showMessage(_t("Error de conexión. Inténtelo nuevamente."), 'danger');
        } finally {
            this.state.isProcessing = false;
            this.ui.unblock();
        }
    }

    /**
     * Envía asistencia con teléfono guardado
     */
    async quickSubmit() {
        console.log("[ATTENDANCE_PHONE_ONLY] Envío rápido con teléfono guardado");
        const phone = this.state.phone.trim();

        this.state.isProcessing = true;
        this.ui.block();

        try {
            const result = await rpc('/attendance/phone/validate_phone_only', {
                phone: phone,
                token: this.props.token
            });

            if (result.success) {
                const actionText = result.action_type === 'check_in' ? 'Entrada' : 'Salida';
                this.showMessage(
                    _t("%(action)s registrada para %(name)s correctamente", { action: actionText, name: result.name }),
                    'success'
                );

                // Permanecer y limpiar mensaje al rato
                setTimeout(() => {
                    this.state.message = "";
                    // Actualizar estado del empleado después del fichaje
                    this.checkEmployeeStatus();
                }, 2000);

            } else {
                this.showMessage(_t("Teléfono no reconocido. Por favor ingrese nuevamente."), 'danger');
                StorageManager.clearCredentials();
            }

        } catch (error) {
            console.error("[ATTENDANCE_PHONE_ONLY] Error:", error);
            this.showMessage(_t("Error de conexión"), 'danger');
        } finally {
            this.state.isProcessing = false;
            this.ui.unblock();
        }
    }

    /**
     * Muestra un mensaje en el componente
     */

    showMessage(message, type = 'info') {
        this.state.message = message;
        this.state.messageType = type;

        try {
            if (this.notification && typeof this.notification.add === 'function') {
                this.notification.add(message, { type: type, sticky: type !== 'success' });
            }
        } catch (error) {
            console.warn("[ATTENDANCE_PHONE_ONLY] No se pudo mostrar notificación:", error);
        }
    }
}

// Agregar los componentes a los componentes estáticos del kioskAttendanceApp
kioskAttendanceApp.components = {
    ...kioskAttendanceApp.components,
    KioskPhoneAttendance,
    KioskPhoneOnlyAttendance,
};

// Aplicar patch al kioskAttendanceApp
patch(kioskAttendanceApp.prototype, {

    setup() {
        console.log("[ATTENDANCE_PHONE] Patch setup ejecutado");
        super.setup();

        // Manejar los modos 'phone' y 'phone_only'
        if (this.props.kioskMode === 'phone') {
            console.log("[ATTENDANCE_PHONE] Modo teléfono + PIN detectado");
            this.state.active_display = "phone";
        } else if (this.props.kioskMode === 'phone_only') {
            console.log("[ATTENDANCE_PHONE] Modo solo teléfono detectado");
            this.state.active_display = "phone_only";
        }

        console.log("[ATTENDANCE_PHONE] Estado inicial:", this.state.active_display);
    },

    /**
     * Override del método setSetting para manejar los modos de teléfono
     */
    async setSetting(mode) {
        console.log("[ATTENDANCE_PHONE] setSetting llamado con modo:", mode);

        if (mode === 'phone' || mode === 'phone_only') {
            console.log("[ATTENDANCE_PHONE] Configurando modo:", mode);

            try {
                await rpc("/hr_attendance/set_settings", {
                    token: this.props.token,
                    mode: mode,
                });

                this.props.kioskMode = mode;
                this.state.active_display = mode;

                console.log("[ATTENDANCE_PHONE] Modo configurado exitosamente:", mode);
            } catch (error) {
                console.error("[ATTENDANCE_PHONE] Error configurando modo:", error);
                this.state.active_display = mode;
            }
        } else {
            return super.setSetting(mode);
        }
    },

    /**
     * Override del método switchDisplay para soportar 'phone' y 'phone_only'
     */
    switchDisplay(screen) {
        console.log("[ATTENDANCE_PHONE] switchDisplay llamado con:", screen);
        const displays = ["main", "greet", "manual", "pin", "settings", "phone", "phone_only"];
        if (displays.includes(screen)) {
            this.state.active_display = screen;
        } else {
            this.state.active_display = "main";
        }
    },

    /**
     * Override del método kioskReturn para manejar el regreso desde modos de teléfono
     */
    kioskReturn() {
        console.log("[ATTENDANCE_PHONE] kioskReturn llamado, display actual:", this.state.active_display);

        if (this.state.active_display === "phone" || this.state.active_display === "phone_only") {
            console.log("[ATTENDANCE_PHONE] Regresando a configuración");
            this.switchDisplay("settings");
            return;
        }

        return super.kioskReturn();
    },

    onPhoneAttendanceRegistered(result) {
        console.log("[ATTENDANCE_PHONE] Asistencia registrada, datos:", result);
    }
});

console.log("[ATTENDANCE_PHONE] ✅ Módulo y patches inicializados correctamente");

