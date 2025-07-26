/** @odoo-module **/

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { useState } from "@odoo/owl";

export class UomSelectionPopup extends AbstractAwaitablePopup {
    static template = "xtendoo_pos_uom_selection.UomSelectionPopup";

    setup() {
        super.setup();
        this.state = useState({
            selectedUom: this.props.currentUom,
        });
    }

    /**
     * Selecciona una unidad de medición
     */
    selectUom(uom) {
        this.state.selectedUom = uom.id;
    }

    /**
     * Confirma la selección
     */
    confirm() {
        const selectedUom = this.props.uoms.find(uom => uom.id === this.state.selectedUom);
        this.resolve({ confirmed: true, payload: { selectedUom } });
    }

    /**
     * Cancela la selección
     */
    cancel() {
        this.resolve({ confirmed: false, payload: null });
    }

    /**
     * Verifica si una UoM está seleccionada
     */
    isSelected(uom) {
        return uom.id === this.state.selectedUom;
    }

    /**
     * Obtiene el factor de conversión para mostrar información útil
     */
    getConversionInfo(uom) {
        const baseUom = this.props.uoms.find(u => u.uom_type === 'reference');
        if (!baseUom || uom.id === baseUom.id) {
            return '';
        }

        if (uom.uom_type === 'bigger') {
            return `(1 ${uom.name} = ${uom.factor_inv} ${baseUom.name})`;
        } else if (uom.uom_type === 'smaller') {
            return `(${uom.factor} ${uom.name} = 1 ${baseUom.name})`;
        }

        return '';
    }
}
