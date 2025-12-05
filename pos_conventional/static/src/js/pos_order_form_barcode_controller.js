/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Controlador de formulario personalizado para órdenes POS
 * que captura códigos de barras escaneados con lectores USB.
 *
 * El lector de códigos de barras funciona como un teclado,
 * enviando caracteres muy rápido seguidos de Enter.
 *
 * Añade productos directamente a las líneas del pedido sin necesidad
 * de guardar el pedido primero.
 */
export class PosOrderBarcodeFormController extends FormController {
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.notification = useService("notification");

        // Buffer para acumular caracteres del escáner
        this.barcodeBuffer = "";
        // Timestamp del último carácter recibido
        this.lastKeyTime = 0;
        // Timeout para detectar fin de escaneo
        this.barcodeTimeout = null;
        // Tiempo máximo entre teclas para considerarlo escaneo (ms)
        // Aumentado a 150ms para dar más margen a escáneres lentos
        this.maxTimeBetweenKeys = 150;
        // Longitud mínima del código de barras
        this.minBarcodeLength = 3;
        // Flag para evitar procesamiento duplicado
        this.isProcessing = false;

        // Bind del handler para poder removerlo después
        this.boundKeydownHandler = this.onKeyDown.bind(this);

        onMounted(() => {
            // Añadir listener global de keydown
            document.addEventListener("keydown", this.boundKeydownHandler, true);
        });

        onWillUnmount(() => {
            // Limpiar listener al desmontar
            document.removeEventListener("keydown", this.boundKeydownHandler, true);
            if (this.barcodeTimeout) {
                clearTimeout(this.barcodeTimeout);
            }
        });
    }

    /**
     * Handler para eventos keydown.
     * Detecta si los caracteres vienen de un escáner USB
     * (caracteres rápidos seguidos de Enter).
     */
    onKeyDown(ev) {
        const now = Date.now();
        const timeDiff = now - this.lastKeyTime;

        // Ignorar teclas modificadoras solas
        if (["Shift", "Control", "Alt", "Meta", "CapsLock", "Escape"].includes(ev.key)) {
            return;
        }

        // Ignorar teclas de función y otras teclas especiales (excepto Enter/Tab)
        if (ev.key.length > 1 && ev.key !== "Enter" && ev.key !== "Tab") {
            return;
        }

        // Manejar Enter o Tab - finalizan el escaneo
        if (ev.key === "Enter" || ev.key === "Tab") {
            if (this.barcodeTimeout) {
                clearTimeout(this.barcodeTimeout);
                this.barcodeTimeout = null;
            }

            // Si tenemos un buffer acumulado suficiente, procesar
            if (this.barcodeBuffer.length >= this.minBarcodeLength) {
                ev.preventDefault();
                ev.stopPropagation();
                ev.stopImmediatePropagation();
                const barcode = this.barcodeBuffer;
                this.barcodeBuffer = "";
                this.lastKeyTime = 0;
                console.log("Barcode escaneado:", barcode);
                this.processBarcode(barcode);
                return false;
            }
            // Si no hay buffer suficiente, resetear y dejar pasar
            this.barcodeBuffer = "";
            this.lastKeyTime = 0;
            return;
        }

        // Detectar si es entrada rápida (posible escaneo)
        const isRapidInput = this.lastKeyTime > 0 && timeDiff < this.maxTimeBetweenKeys;

        // Si pasó mucho tiempo desde la última tecla, resetear buffer
        if (this.lastKeyTime > 0 && timeDiff > this.maxTimeBetweenKeys) {
            this.barcodeBuffer = "";
        }

        // Acumular el carácter
        this.barcodeBuffer += ev.key;
        this.lastKeyTime = now;

        // IMPORTANTE: Prevenir el evento SIEMPRE que estemos acumulando caracteres rápidos
        // Esto evita que los caracteres se escriban en inputs mientras escaneamos
        if (this.barcodeBuffer.length >= 1) {
            ev.preventDefault();
            ev.stopPropagation();
            ev.stopImmediatePropagation();
        }

        // Limpiar timeout anterior
        if (this.barcodeTimeout) {
            clearTimeout(this.barcodeTimeout);
        }

        // Configurar timeout para procesar si no llega Enter
        this.barcodeTimeout = setTimeout(() => {
            if (this.barcodeBuffer.length >= this.minBarcodeLength) {
                const barcode = this.barcodeBuffer;
                this.barcodeBuffer = "";
                this.lastKeyTime = 0;
                console.log("Barcode escaneado (timeout):", barcode);
                this.processBarcode(barcode);
            } else {
                // Si no es suficientemente largo, no era un código de barras
                // Limpiar buffer
                this.barcodeBuffer = "";
                this.lastKeyTime = 0;
            }
        }, this.maxTimeBetweenKeys + 50);

        return false;
    }


    /**
     * Procesa el código de barras escaneado.
     * Busca el producto y lo añade directamente a las líneas del formulario.
     */
    async processBarcode(barcode) {
        if (this.isProcessing) {
            return;
        }

        // Limpiar el código de barras
        barcode = barcode.trim();

        if (!barcode || barcode.length < this.minBarcodeLength) {
            return;
        }

        this.isProcessing = true;

        try {
            const record = this.model.root;

            // Obtener datos del pedido actual para contexto
            const orderId = record.resId;
            const pricelistId = record.data.pricelist_id ? record.data.pricelist_id[0] : false;
            const fiscalPositionId = record.data.fiscal_position_id ? record.data.fiscal_position_id[0] : false;
            const partnerId = record.data.partner_id ? record.data.partner_id[0] : false;

            // Llamar a Python para obtener los datos completos de la línea
            const result = await this.orm.call(
                "pos.order",
                "get_product_line_data_by_barcode",
                [],
                {
                    barcode: barcode,
                    pricelist_id: pricelistId,
                    fiscal_position_id: fiscalPositionId,
                    partner_id: partnerId,
                }
            );

            if (!result.success) {
                this.notification.add(
                    result.message,
                    { type: "warning", title: "Producto no encontrado" }
                );
                return;
            }

            // Añadir el producto a las líneas del pedido
            await this.addProductToLines(result.product, result.line_vals);

        } catch (error) {
            console.error("Error al procesar código de barras:", error);
            this.notification.add(
                `Error al procesar código: ${barcode}`,
                { type: "danger", title: "Error de escaneo" }
            );
        } finally {
            this.isProcessing = false;
        }
    }

    /**
     * Añade un producto a las líneas del pedido actual.
     * Si el pedido es nuevo, lo guarda primero.
     */
    async addProductToLines(product, lineVals) {
        const record = this.model.root;

        // Si el pedido es nuevo, guardarlo primero
        if (record.isNew) {
            try {
                // Guardar el pedido
                await record.save();
            } catch (error) {
                console.error("Error al guardar el pedido:", error);
                this.notification.add(
                    "Debe guardar el pedido antes de escanear productos.",
                    { type: "warning", title: "Pedido no guardado" }
                );
                return;
            }
        }

        // Ahora el pedido está guardado, añadir línea vía RPC
        const orderId = record.resId;
        if (!orderId) {
            this.notification.add(
                "No se puede identificar el pedido actual.",
                { type: "warning", title: "Error" }
            );
            return;
        }

        await this.addLineViaRPC(orderId, product, lineVals);
    }

    /**
     * Añade una línea vía RPC para pedidos ya guardados
     */
    async addLineViaRPC(orderId, product, lineVals) {
        try {
            // Llamar al método Python para añadir la línea
            const result = await this.orm.call(
                "pos.order",
                "add_product_by_barcode",
                [orderId],
                {
                    product_id: product.id,
                }
            );

            if (result.success) {
                this.notification.add(
                    result.message,
                    { type: "success", title: "Producto añadido" }
                );
                // Recargar el registro para mostrar la nueva línea
                await this.model.root.load();
            } else {
                this.notification.add(
                    result.message,
                    { type: "warning", title: "Error" }
                );
            }
        } catch (error) {
            console.error("Error al añadir línea vía RPC:", error);
            this.notification.add(
                `Error al añadir producto: ${error.message || error}`,
                { type: "danger", title: "Error" }
            );
        }
    }
}

// Registrar la vista personalizada para pos.order
export const posOrderBarcodeFormView = {
    ...formView,
    Controller: PosOrderBarcodeFormController,
};

registry.category("views").add("pos_order_barcode_form", posOrderBarcodeFormView);
