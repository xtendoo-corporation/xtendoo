import { barcodeService as barcodeServiceDefinition } from "@barcodes/barcode_service";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillUnmount, useRef, xml } from "@odoo/owl";

const BARCODE_EVENTS_ATTR = "barcode_events";
const MANAGED_DATASET_KEY = "xtendooSaleBarcodeScannerManaged";
const ORIGINAL_DATASET_KEY = "xtendooSaleBarcodeScannerOriginal";
const EDITABLE_SELECTOR = 'input, textarea, [contenteditable="true"]';

function isNodeWithin(node, container) {
    return node instanceof Node && container?.contains(node);
}

function isEditable(element) {
    return element?.matches?.(EDITABLE_SELECTOR);
}

function isSpecialKey(key, event) {
    return !["Control", "Alt"].includes(key) && (key.length > 1 || event.metaKey);
}

function isEndCharacter(key) {
    return /(Enter|Tab)/.test(key);
}

function cleanBarcode(barcode) {
    return barcodeServiceDefinition.cleanBarcode(barcode);
}

function getBarcodeTimeout() {
    return barcodeServiceDefinition.maxTimeBetweenKeysInMs;
}

function captureEditableState(element) {
    if (!isEditable(element)) {
        return null;
    }
    if (element.matches('[contenteditable="true"]')) {
        return {
            element,
            html: element.innerHTML,
            text: element.textContent,
            type: "contenteditable",
        };
    }
    return {
        element,
        selectionEnd: element.selectionEnd,
        selectionStart: element.selectionStart,
        type: "input",
        value: element.value,
    };
}

function applyBufferedText(state, text) {
    if (!state?.element?.isConnected) {
        return;
    }
    if (state.type === "contenteditable") {
        state.element.textContent = `${state.text}${text}`;
        return;
    }
    const selectionStart = state.selectionStart ?? state.value.length;
    const selectionEnd = state.selectionEnd ?? selectionStart;
    state.element.value =
        state.value.slice(0, selectionStart) + text + state.value.slice(selectionEnd);
    const nextPosition = selectionStart + text.length;
    if (typeof state.element.setSelectionRange === "function") {
        state.element.setSelectionRange(nextPosition, nextPosition);
    }
    state.element.dispatchEvent(new Event("input", { bubbles: true }));
}

export class SaleBarcodeScannerField extends Component {
    static props = { ...standardFieldProps };
    static supportedTypes = ["char"];
    static template = xml`<div t-ref="root" class="o_xtendoo_sale_barcode_scanner d-none"/>`;

    setup() {
        this.rootRef = useRef("root");
        this.barcodeService = useService("barcode");
        useBus(this.barcodeService.bus, "barcode_scanned", this.onBarcodeScanned.bind(this));
        onMounted(() => this._mountBarcodeScope());
        onWillUnmount(() => this._unmountBarcodeScope());
    }

    _mountBarcodeScope() {
        this.formElement = this.rootRef.el?.closest(".o_form_view, .o_form_renderer");
        if (!this.formElement) {
            return;
        }
        this._onKeydownCapture = this._handleKeydownCapture.bind(this);
        this.formElement.addEventListener("keydown", this._onKeydownCapture, true);
        this._markEditableElements();
        this.observer = new MutationObserver(() => this._markEditableElements());
        this.observer.observe(this.formElement, { childList: true, subtree: true });
    }

    _unmountBarcodeScope() {
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
        }
        if (this.formElement && this._onKeydownCapture) {
            this.formElement.removeEventListener("keydown", this._onKeydownCapture, true);
            this._onKeydownCapture = null;
        }
        this._clearPendingBarcodeCapture();
        if (!this.formElement) {
            return;
        }
        for (const element of this.formElement.querySelectorAll(EDITABLE_SELECTOR)) {
            if (!element.dataset[MANAGED_DATASET_KEY]) {
                continue;
            }
            const originalValue = element.dataset[ORIGINAL_DATASET_KEY];
            if (originalValue === "__none__") {
                element.removeAttribute(BARCODE_EVENTS_ATTR);
            } else {
                element.setAttribute(BARCODE_EVENTS_ATTR, originalValue);
            }
            delete element.dataset[MANAGED_DATASET_KEY];
            delete element.dataset[ORIGINAL_DATASET_KEY];
        }
    }

    _markEditableElements() {
        for (const element of this.formElement.querySelectorAll(EDITABLE_SELECTOR)) {
            if (element.dataset[MANAGED_DATASET_KEY]) {
                continue;
            }
            element.dataset[MANAGED_DATASET_KEY] = "1";
            element.dataset[ORIGINAL_DATASET_KEY] =
                element.getAttribute(BARCODE_EVENTS_ATTR) ?? "__none__";
            element.setAttribute(BARCODE_EVENTS_ATTR, "true");
        }
    }

    _clearPendingBarcodeCapture() {
        if (this.pendingBarcodeCapture?.timeoutId) {
            clearTimeout(this.pendingBarcodeCapture.timeoutId);
        }
        this.pendingBarcodeCapture = null;
    }

    _isBarcodeSequence(rawBarcode) {
        return cleanBarcode(rawBarcode).length >= 3;
    }

    _finalizePendingBarcodeCapture() {
        const pendingBarcodeCapture = this.pendingBarcodeCapture;
        this._clearPendingBarcodeCapture();
        if (!pendingBarcodeCapture || this._isBarcodeSequence(pendingBarcodeCapture.rawBarcode)) {
            return;
        }
        applyBufferedText(pendingBarcodeCapture.snapshot, cleanBarcode(pendingBarcodeCapture.rawBarcode));
    }

    _refreshPendingBarcodeCaptureTimeout() {
        if (!this.pendingBarcodeCapture) {
            return;
        }
        if (this.pendingBarcodeCapture.timeoutId) {
            clearTimeout(this.pendingBarcodeCapture.timeoutId);
        }
        this.pendingBarcodeCapture.timeoutId = setTimeout(
            () => this._finalizePendingBarcodeCapture(),
            getBarcodeTimeout()
        );
    }

    _handleKeydownCapture(event) {
        const target = event.target;
        if (!isNodeWithin(target, this.formElement) || !isEditable(target) || !event.key) {
            return;
        }
        const endCharacter = isEndCharacter(event.key);
        if (isSpecialKey(event.key, event) && !endCharacter) {
            return;
        }

        if (!this.pendingBarcodeCapture && endCharacter) {
            return;
        }

        const now = Date.now();
        const isNewSequence =
            !this.pendingBarcodeCapture ||
            this.pendingBarcodeCapture.target !== target ||
            now - this.pendingBarcodeCapture.lastEventAt > getBarcodeTimeout();

        if (isNewSequence) {
            this._finalizePendingBarcodeCapture();
            if (endCharacter) {
                return;
            }
            this.pendingBarcodeCapture = {
                rawBarcode: "",
                snapshot: captureEditableState(target),
                target,
            };
        }

        if (!this.pendingBarcodeCapture) {
            return;
        }

        this.pendingBarcodeCapture.lastEventAt = now;
        if (!endCharacter) {
            event.preventDefault();
            this.pendingBarcodeCapture.rawBarcode += event.key;
            this._refreshPendingBarcodeCaptureTimeout();
            return;
        }

        if (!this._isBarcodeSequence(this.pendingBarcodeCapture.rawBarcode)) {
            this._finalizePendingBarcodeCapture();
            return;
        }

        event.preventDefault();
        this._clearPendingBarcodeCapture();
    }

    async onBarcodeScanned(event) {
        const { barcode, target } = event.detail;
        if (!barcode || !isNodeWithin(target, this.formElement)) {
            return;
        }
        this._clearPendingBarcodeCapture();
        await this.props.record.update({ [this.props.name]: barcode });
    }
}

registry.category("fields").add("xtendoo_sale_barcode_scanner", {
    component: SaleBarcodeScannerField,
});

