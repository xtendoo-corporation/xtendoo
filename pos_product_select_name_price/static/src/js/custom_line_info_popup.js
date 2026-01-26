/** @odoo-module */

import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class CustomLineInfoPopup extends Component {
    static template = "pos_note.CustomLineInfoPopup";
    static components = { Dialog };
    static props = {
        title: { type: String, optional: true },
        productName: { type: String, optional: true },
        defaultPrice: { type: Number, optional: true },
        getPayload: Function,
        close: Function,
    };
    static defaultProps = {
        title: _t("Información personalizada"),
        productName: "",
        defaultPrice: 0,
    };

    setup() {
        this.state = useState({
            customName: this.props.productName,
            customPrice: this.props.defaultPrice,
            customPriceDisplay: this.formatPriceForDisplay(this.props.defaultPrice),
            nameError: false,
            priceError: false,
        });
        this.nameInputRef = useRef("nameInput");

        onMounted(() => {
            if (this.nameInputRef.el) {
                this.nameInputRef.el.focus();
                this.nameInputRef.el.select();
            }
        });
    }

    /**
     * Formatea el precio para mostrar con coma como separador decimal
     */
    formatPriceForDisplay(price) {
        if (price === undefined || price === null || isNaN(price)) {
            return "0,00";
        }
        return price.toFixed(2).replace('.', ',');
    }

    /**
     * Parsea el precio ingresado (acepta coma o punto como separador decimal)
     */
    parsePriceInput(value) {
        if (!value) return 0;
        // Reemplazar coma por punto para parsear
        const normalized = value.toString().replace(',', '.');
        const parsed = parseFloat(normalized);
        return isNaN(parsed) ? 0 : parsed;
    }

    get formattedPrice() {
        return this.state.customPriceDisplay;
    }

    onNameChange(ev) {
        this.state.customName = ev.target.value;
        this.state.nameError = false;
    }

    onPriceChange(ev) {
        const inputValue = ev.target.value;
        // Guardar el valor mostrado tal como el usuario lo escribe
        this.state.customPriceDisplay = inputValue;
        // Parsear el valor (acepta coma o punto)
        this.state.customPrice = this.parsePriceInput(inputValue);
        this.state.priceError = false;
    }

    confirm() {
        // Validaciones
        let hasError = false;

        if (!this.state.customName || this.state.customName.trim() === "") {
            this.state.nameError = true;
            hasError = true;
        }

        if (this.state.customPrice <= 0) {
            this.state.priceError = true;
            hasError = true;
        }

        if (hasError) {
            return;
        }

        this.props.getPayload({
            customName: this.state.customName.trim(),
            customPrice: this.state.customPrice,
        });
        this.props.close();
    }

    cancel() {
        this.props.close();
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            this.confirm();
        } else if (ev.key === "Escape") {
            this.cancel();
        }
    }
}
