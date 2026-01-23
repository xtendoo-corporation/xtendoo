/**
 * Parche global para asegurar que el contexto de creación/edición de registros multiempresa incluya company_id
 * Funciona para cualquier modelo con campo company_id (productos, contactos, etc.)
 */
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { patch } from "@web/core/utils/patch";

const originalGetCreationContext = Many2XAutocomplete.prototype.getCreationContext;

patch(Many2XAutocomplete.prototype, {
    getCreationContext(value) {
        // Llamar al método original si existe, si no, usar un objeto vacío
        const ctx = originalGetCreationContext
            ? originalGetCreationContext.call(this, value)
            : {};
        console.log("[xtendoo_encapsulate_companies] Contexto original:", ctx);
        // Si ya tiene company_id, no hacer nada
        if (ctx.company_id) {
            console.log("[xtendoo_encapsulate_companies] company_id ya presente:", ctx.company_id);
            return ctx;
        }
        // Buscar company_id en el contexto del registro actual
        let companyId = null;
        if (this.props && this.props.record && this.props.record.data && this.props.record.data.company_id) {
            companyId = this.props.record.data.company_id;
            console.log("[xtendoo_encapsulate_companies] company_id desde record.data:", companyId);
        } else if (this.props && this.props.context && this.props.context.company_id) {
            companyId = this.props.context.company_id;
            console.log("[xtendoo_encapsulate_companies] company_id desde props.context:", companyId);
        } else if (ctx.allowed_company_ids && ctx.allowed_company_ids.length) {
            companyId = ctx.allowed_company_ids[0];
            console.log("[xtendoo_encapsulate_companies] company_id desde allowed_company_ids:", companyId);
        } else if (typeof odoo !== 'undefined' && odoo.session_info && odoo.session_info.company_id) {
            companyId = odoo.session_info.company_id;
            console.log("[xtendoo_encapsulate_companies] company_id desde odoo.session_info:", companyId);
        } else {
            console.log("[xtendoo_encapsulate_companies] company_id no encontrado");
        }
        if (companyId) {
            ctx.company_id = companyId;
            ctx.default_company_id = companyId;
            console.log("[xtendoo_encapsulate_companies] company_id asignado:", companyId);
        }
        console.log("[xtendoo_encapsulate_companies] Contexto final:", ctx);
        return ctx;
    },
});
