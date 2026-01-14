/** @odoo-module **/

import { InvoiceExtractFormRenderer } from '@account_invoice_extract/js/invoice_extract_form';
import { registry } from "@web/core/registry";
import { AccountMoveFormView } from '@account/components/account_move_form/account_move_form';
import { patch } from "@web/core/utils/patch";

/**
 * This patch fixes a JavaScript error that occurs when focusing on fields within x2many relations
 * (like analytic_distribution in invoice lines) while using the invoice extract feature.
 *
 * The error "Cannot read properties of undefined (reading 'fields')" happens because the original
 * code tries to access _config.fields on a parent field that might not be properly initialized yet.
 *
 * The fix adds proper validation to ensure the parent field exists and has the necessary configuration
 * before trying to access its fields.
 */
patch(InvoiceExtractFormRenderer.prototype, {
    /**
     * Override getBoxType to add proper validation for x2many fields
     * @override
     */
    getBoxType(fullFieldName) {
        if (!fullFieldName) {
            return false;
        }
        let modelFieldType;
        if (fullFieldName.includes('.')) {
            const [parentField, fieldName] = fullFieldName.split('.');
            // Add validation to check if parent field exists and has the necessary configuration
            const parentFieldData = this.props.record.data[parentField];
            if (!parentFieldData || !parentFieldData._config || !parentFieldData._config.fields) {
                // If the parent field or its configuration doesn't exist, return false
                return false;
            }
            const fieldConfig = parentFieldData._config.fields[fieldName];
            if (!fieldConfig) {
                // If the field configuration doesn't exist, return false
                return false;
            }
            modelFieldType = fieldConfig.type;
        }
        else {
            const fieldConfig = this.props.record.fields[fullFieldName];
            if (!fieldConfig) {
                return false;
            }
            modelFieldType = fieldConfig.type;
        }

        // Field type to box type mapping
        const FIELD_TO_BOX_TYPE_MAPPING = {
            'char': 'word',
            'text': 'word',
            'html': 'word',
            'many2one': 'word',
            'integer': 'number',
            'float': 'number',
            'monetary': 'number',
            'date': 'date',
            'datetime': 'date',
        };

        return FIELD_TO_BOX_TYPE_MAPPING[modelFieldType];
    }
});

