/**
 * Parche para asegurar que el contexto de creación/edición de productos incluya company_id
 */
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { patch } from "@web/core/utils/patch";

// Guardar referencia al método original
const originalGetCreationContext = Many2XAutocomplete.prototype.getCreationContext;

patch(Many2XAutocomplete.prototype, {
    getCreationContext(value) {
        // Llamar al método original si existe, si no, usar un objeto vacío
        const ctx = originalGetCreationContext
            ? originalGetCreationContext.call(this, value)
            : {};
        // Si ya tiene company_id, no hacer nada
        if (ctx.company_id) {
            return ctx;
        }
        // Buscar company_id en el contexto del registro actual
        let companyId = null;
        if (this.props && this.props.record && this.props.record.data && this.props.record.data.company_id) {
            companyId = this.props.record.data.company_id;
        } else if (this.props && this.props.context && this.props.context.company_id) {
            companyId = this.props.context.company_id;
        } else if (ctx.allowed_company_ids && ctx.allowed_company_ids.length) {
            companyId = ctx.allowed_company_ids[0];
        } else if (typeof odoo !== 'undefined' && odoo.session_info && odoo.session_info.company_id) {
            companyId = odoo.session_info.company_id;
        } else {
        }
        if (companyId) {
            ctx.company_id = companyId;
            //Sin este paso en el crear y editar de facturas en la linea, no se asigna la compañía correctamente al producto
            ctx.default_company_id = companyId;
        }
        return ctx;
    },
});
