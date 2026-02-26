from odoo import models, api, fields, _
import logging

_logger = logging.getLogger(__name__)

# Modelos que NO deben tener company_id asignado automáticamente
EXCLUDED_MODELS = [
    'ir.sequence',
    'ir.sequence.date_range',
    'ir.rule',
    'ir.model',
    'ir.model.fields',
    'ir.model.access',
    'ir.ui.view',
    'ir.ui.menu',
    'ir.actions',
    'ir.config_parameter',
    'res.config.settings',
]


# Aplicamos el override directamente al modelo base para evitar el bucle de herencia.
class Base(models.AbstractModel):
    _inherit = 'base'  # Indicamos que esta clase modifica la clase 'base'

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info(f"[xtendoo_encapsulate_companies_crm] Creando registros en modelo: {self._name}")
        # No asignar company_id a modelos excluidos
        if self._name in EXCLUDED_MODELS or self._name.startswith('ir.actions.'):
            _logger.info(f"[xtendoo_encapsulate_companies_crm] Modelo excluido: {self._name}. No se asigna company_id.")
            return super(Base, self).create(vals_list)

        def get_company_id():
            company_ctx = self.env.context.get('allowed_company_ids')
            _logger.info(f"[xtendoo_encapsulate_companies_crm] allowed_company_ids en contexto: {company_ctx}")

            try:
                if company_ctx is not None:
                    try:
                        length = len(company_ctx)
                    except Exception:
                        length = None
                    if length and length > 1:
                        try:
                            first = company_ctx[0]
                            _logger.info(f"[xtendoo_encapsulate_companies_crm] Usuario con >1 company activa; usando allowed_company_ids[0]: {first}")
                            return first
                        except Exception:
                            _logger.info(f"[xtendoo_encapsulate_companies_crm] allowed_company_ids no indexable, devolviendo valor directo: {company_ctx}")
                            return company_ctx
            except Exception:
                _logger.exception("[xtendoo_encapsulate_companies_crm] Error evaluando allowed_company_ids")

            try:
                if hasattr(self.env, 'user') and self.env.user and self.env.user.company_id:
                    _logger.info(f"[xtendoo_encapsulate_companies_crm] Usando company_id de usuario activo: {self.env.user.company_id.id}")
                    return self.env.user.company_id.id
            except Exception:
                _logger.exception("[xtendoo_encapsulate_companies_crm] Error obteniendo company_id desde env.user.company_id")

            try:
                if company_ctx:
                    try:
                        first = company_ctx[0]
                        _logger.info(f"[xtendoo_encapsulate_companies_crm] allowed_company_ids tiene 1 elemento; usando: {first}")
                        return first
                    except Exception:
                        _logger.info(f"[xtendoo_encapsulate_companies_crm] allowed_company_ids usado directamente: {company_ctx}")
                        return company_ctx
            except Exception:
                _logger.exception("[xtendoo_encapsulate_companies_crm] Error procesando allowed_company_ids as fallback")

            try:
                _logger.info(f"[xtendoo_encapsulate_companies_crm] Fallback usando env.company: {self.env.company.id}")
                return self.env.company.id
            except Exception:
                _logger.exception("[xtendoo_encapsulate_companies_crm] Error obteniendo company_id desde env.company")
                return False

        def assign_company(val_dict):
            original_company = None
            if isinstance(val_dict, dict):
                original_company = val_dict.get('company_id', None)
            
            is_falsy = original_company in (False, None, 0) or (isinstance(original_company, (list, tuple)) and len(original_company) == 0)

            should_assign = ('company_id' in self._fields) and (('company_id' not in val_dict) or is_falsy)
            if should_assign:
                new_company = get_company_id()
                val_dict['company_id'] = new_company
                _logger.info(
                    f"[xtendoo_encapsulate_companies_crm] Asignando company_id={new_company} automáticamente "
                    f"al crear un registro en el modelo {self._name}. Vals: {val_dict}"
                )

        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        for val_dict in vals_list:
            assign_company(val_dict)

        return super(Base, self).create(vals_list)

    @api.model
    def default_get(self, fields_list):
        defaults = super(Base, self).default_get(fields_list)
        try:
            if 'company_id' in fields_list:
                orig = defaults.get('company_id', None)
                if not orig:
                    company_ctx = self.env.context.get('allowed_company_ids')
                    if company_ctx:
                        if isinstance(company_ctx, (list, tuple)) and len(company_ctx) > 0:
                            defaults['company_id'] = company_ctx[0]
                        else:
                            defaults['company_id'] = company_ctx
                    elif hasattr(self.env, 'user') and self.env.user and self.env.user.company_id:
                        defaults['company_id'] = self.env.user.company_id.id
        except Exception:
            _logger.exception("[xtendoo_encapsulate_companies_crm] Error en default_get al establecer company_id")
        return defaults
