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
    'pos.session',
    'pos.order',
    'pos.order.line',
    'pos.payment',
]


# Aplicamos el override directamente al modelo base para evitar el bucle de herencia.
class Base(models.AbstractModel):
    _inherit = 'base'  # Indicamos que esta clase modifica la clase 'base'

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info(f"[xtendoo_encapsulate_companies] Creando registros en modelo: {self._name}")
        # No asignar company_id a modelos excluidos
        if self._name in EXCLUDED_MODELS or self._name.startswith('ir.actions.'):
            _logger.info(f"[xtendoo_encapsulate_companies] Modelo excluido: {self._name}. No se asigna company_id.")
            return super(Base, self).create(vals_list)

        def get_company_id():
            """Regla requerida:
            - Si el usuario tiene más de una compañía activa (allowed_company_ids con len>1) usar allowed_company_ids[0]
            - Si no, usar la compañía activa del usuario (env.user.company_id.id)
            - Si no hay user.company_id, usar allowed_company_ids[0] si existe
            - Finalmente fallback a env.company.id
            """
            company_ctx = self.env.context.get('allowed_company_ids')
            _logger.info(f"[xtendoo_encapsulate_companies] allowed_company_ids en contexto: {company_ctx}")

            # Si hay más de una compañía activa en contexto, usar la primera
            try:
                if company_ctx is not None:
                    try:
                        length = len(company_ctx)
                    except Exception:
                        length = None
                    if length and length > 1:
                        try:
                            first = company_ctx[0]
                            _logger.info(f"[xtendoo_encapsulate_companies] Usuario con >1 company activa; usando allowed_company_ids[0]: {first}")
                            return first
                        except Exception:
                            _logger.info(f"[xtendoo_encapsulate_companies] allowed_company_ids no indexable, devolviendo valor directo: {company_ctx}")
                            return company_ctx
            except Exception:
                _logger.exception("[xtendoo_encapsulate_companies] Error evaluando allowed_company_ids")

            # Si no hay >1, preferir la compañía activa del usuario
            try:
                if hasattr(self.env, 'user') and self.env.user and self.env.user.company_id:
                    _logger.info(f"[xtendoo_encapsulate_companies] Usando company_id de usuario activo: {self.env.user.company_id.id}")
                    return self.env.user.company_id.id
            except Exception:
                _logger.exception("[xtendoo_encapsulate_companies] Error obteniendo company_id desde env.user.company_id")

            # Si no hay company_id en user, usar allowed_company_ids[0] si existe
            try:
                if company_ctx:
                    try:
                        first = company_ctx[0]
                        _logger.info(f"[xtendoo_encapsulate_companies] allowed_company_ids tiene 1 elemento; usando: {first}")
                        return first
                    except Exception:
                        _logger.info(f"[xtendoo_encapsulate_companies] allowed_company_ids usado directamente: {company_ctx}")
                        return company_ctx
            except Exception:
                _logger.exception("[xtendoo_encapsulate_companies] Error procesando allowed_company_ids como fallback")

            # Fallback final: env.company
            try:
                _logger.info(f"[xtendoo_encapsulate_companies] Fallback usando env.company: {self.env.company.id}")
                return self.env.company.id
            except Exception:
                _logger.exception("[xtendoo_encapsulate_companies] Error obteniendo company_id desde env.company")
                return False

        def assign_company(val_dict):
            # Solo asignar si el campo company_id existe en el modelo
            # Si company_id NO está presente en vals o está presente pero con valor falso (None/False/0/[]), lo asignamos
            original_company = None
            if isinstance(val_dict, dict):
                original_company = val_dict.get('company_id', None)
            _logger.info(f"[xtendoo_encapsulate_companies] Valor original de company_id en vals: {original_company!r} (tipo: {type(original_company)})")

            # Considerar falsy values que indican que no se ha establecido: False, None, 0, empty list/tuple
            is_falsy = original_company in (False, None, 0) or (isinstance(original_company, (list, tuple)) and len(original_company) == 0)

            should_assign = ('company_id' in self._fields) and (('company_id' not in val_dict) or is_falsy)
            if should_assign:
                new_company = get_company_id()
                val_dict['company_id'] = new_company
                _logger.info(
                    f"[xtendoo_encapsulate_companies] Asignando company_id={new_company} automáticamente "
                    f"al crear un registro en el modelo {self._name}. Vals: {val_dict}"
                )
            else:
                _logger.info(f"[xtendoo_encapsulate_companies] No se asigna company_id en modelo {self._name}. Vals: {val_dict}")

        # Asegurar que vals_list es una lista
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        # Procesar cada elemento
        for val_dict in vals_list:
            assign_company(val_dict)

        _logger.info(f"[xtendoo_encapsulate_companies] Vals final para create en {self._name}: {vals_list}")
        return super(Base, self).create(vals_list)

    @api.model
    def default_get(self, fields_list):
        """Asegurar que al abrir un formulario desde 'Nuevo' en lista, si el default de company_id es falsy
        lo rellenamos con allowed_company_ids o la compañía del usuario."""
        defaults = super(Base, self).default_get(fields_list)
        try:
            if 'company_id' in fields_list:
                orig = defaults.get('company_id', None)
                _logger.info(f"[xtendoo_encapsulate_companies] default_get en {self._name}, valor original de company_id: {orig!r}")
                if not orig:
                    # Intentar sacar de contexto
                    company_ctx = self.env.context.get('allowed_company_ids')
                    if company_ctx:
                        if isinstance(company_ctx, (list, tuple)) and len(company_ctx) > 0:
                            defaults['company_id'] = company_ctx[0]
                        else:
                            defaults['company_id'] = company_ctx
                        _logger.info(f"[xtendoo_encapsulate_companies] default_get ha puesto company_id desde allowed_company_ids: {defaults['company_id']}")
                    elif hasattr(self.env, 'user') and self.env.user and self.env.user.company_id:
                        defaults['company_id'] = self.env.user.company_id.id
                        _logger.info(f"[xtendoo_encapsulate_companies] default_get ha puesto company_id desde user.company: {defaults['company_id']}")
        except Exception:
            _logger.exception("[xtendoo_encapsulate_companies] Error en default_get al establecer company_id")
        return defaults

