/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

/**
 * Controlador para captura de código de barras en el formulario de pos.order
 * Se activa automáticamente cuando el modelo es "pos.order"
 *
 * IMPORTANTE: Captura el código de barras ANTES de que se escriba en cualquier campo
 */
patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);

        // Solo activar el scanner si estamos en el formulario de pos.order
        const isPosOrder = this.props.resModel === "pos.order";

        if (isPosOrder) {
            this.barcodeBuffer = "";
            this.lastKeypressTime = 0;
            this.barcodeTimeout = null;
            this.SCAN_TIMEOUT = 50; // ms - tiempo máximo entre teclas del scanner
            this.MIN_BARCODE_LENGTH = 3; // longitud mínima del código de barras
            this.isScanning = false; // Flag para detectar si estamos en medio de un escaneo
            this._barcodeScannerActive = true; // Flag para saber que está activo

            // Vincular métodos al contexto
            this._onKeydown = this._onKeydown.bind(this);
            this._onKeypress = this._onKeypress.bind(this);

            // KEYDOWN se dispara ANTES que el texto se escriba en el campo
            // Esto nos permite PREVENIR que se escriba
            document.addEventListener("keydown", this._onKeydown, true); // true = capture phase
            document.addEventListener("keypress", this._onKeypress, true);
        }
    },

    /**
     * Limpiar listeners al destruir el componente
     */
    onWillUnmount() {
        if (this._barcodeScannerActive) {
            document.removeEventListener("keydown", this._onKeydown, true);
            document.removeEventListener("keypress", this._onKeypress, true);
            if (this.barcodeTimeout) {
                clearTimeout(this.barcodeTimeout);
            }
        }
        super.onWillUnmount();
    },

    /**
     * Evento KEYDOWN - se dispara ANTES de que el carácter se escriba
     * Aquí detectamos si es un escaneo rápido y PREVENIMOS que se escriba
     */
    _onKeydown(ev) {
        const currentTime = Date.now();
        const timeSinceLastKey = currentTime - this.lastKeypressTime;

        // Detectar si es un escaneo rápido (< 50ms entre teclas)
        // Los humanos NO pueden escribir tan rápido
        if (timeSinceLastKey > 0 && timeSinceLastKey < this.SCAN_TIMEOUT && this.barcodeBuffer.length > 0) {
            this.isScanning = true;
        }

        // Si estamos escaneando y NO es Tab/Shift/Ctrl/Alt, prevenir que se escriba
        if (this.isScanning && ev.key.length === 1) {
            ev.preventDefault();
            ev.stopPropagation();
        }

        // Si es Enter y estamos escaneando, procesar
        if (ev.key === "Enter" && this.isScanning) {
            ev.preventDefault();
            ev.stopPropagation();
            this.isScanning = false;
            this._processBarcodeBuffer();
            return;
        }
    },

    /**
     * Evento KEYPRESS - captura el carácter para acumularlo
     */
    _onKeypress(ev) {
        const currentTime = Date.now();
        const timeSinceLastKey = currentTime - this.lastKeypressTime;

        // Si el tiempo entre teclas es muy largo, resetear buffer
        // (probablemente sea escritura humana, no scanner)
        if (timeSinceLastKey > 200) {
            this.barcodeBuffer = "";
            this.isScanning = false;
        }

        // Si es Enter, procesar el código acumulado
        if (ev.key === "Enter") {
            if (this.barcodeBuffer.length >= this.MIN_BARCODE_LENGTH) {
                ev.preventDefault();
                ev.stopPropagation();
                this._processBarcodeBuffer();
            }
            return;
        }

        // Acumular carácter (excepto caracteres de control)
        if (ev.key.length === 1) {
            // Prevenir que se escriba en el campo si estamos escaneando
            if (this.isScanning) {
                ev.preventDefault();
                ev.stopPropagation();
            }

            this.barcodeBuffer += ev.key;
            this.lastKeypressTime = currentTime;

            // Limpiar timeout anterior
            if (this.barcodeTimeout) {
                clearTimeout(this.barcodeTimeout);
            }

            // Establecer timeout para procesar el código
            // Si no se reciben más caracteres en SCAN_TIMEOUT ms, procesar
            this.barcodeTimeout = setTimeout(() => {
                this._processBarcodeBuffer();
            }, this.SCAN_TIMEOUT);
        }
    },

    /**
     * Procesa el buffer de código de barras acumulado
     */
    async _processBarcodeBuffer() {
        const barcode = this.barcodeBuffer.trim();
        this.barcodeBuffer = "";
        this.isScanning = false; // Resetear flag de escaneo

        // Validar longitud mínima
        if (barcode.length < this.MIN_BARCODE_LENGTH) {
            return;
        }

        // Verificar que el pedido esté en estado draft
        if (this.model.root.data.state !== "draft") {
            this.env.services.notification.add(
                this.env._t("Cannot add products to a validated order"),
                { type: "warning" }
            );
            return;
        }

        // Verificar que haya una sesión
        if (!this.model.root.data.session_id) {
            this.env.services.notification.add(
                this.env._t("Please select a session first"),
                { type: "warning" }
            );
            return;
        }

        try {
            // Llamar al método Python para añadir el producto
            const result = await this.model.orm.call(
                "pos.order",
                "add_product_by_barcode",
                [this.model.root.resId, barcode]
            );

            if (result.success) {
                // Recargar el pedido para mostrar la nueva línea
                await this.model.root.load();

                // Notificación de éxito
                this.env.services.notification.add(
                    this.env._t("Product added: %s", result.product_name),
                    { type: "success" }
                );
            } else {
                // Mostrar error
                this.env.services.notification.add(
                    result.message || this.env._t("Product not found with barcode: %s", barcode),
                    { type: "warning" }
                );
            }
        } catch (error) {
            console.error("Error adding product by barcode:", error);
            this.env.services.notification.add(
                this.env._t("Error adding product: %s", error.message || error),
                { type: "danger" }
            );
        }
    },
});

