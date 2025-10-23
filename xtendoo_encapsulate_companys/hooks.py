from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def post_init_check_company_id(env):
    """
    Función que se ejecuta justo después de la instalación del módulo (post-init-hook).
    Audita solo los modelos de los MÓDULOS INSTALADOS que NO tienen el campo 'company_id'.
    """
    _logger.info("=====================================================================")
    _logger.info("AUDITORÍA POST-INSTALACIÓN (Odoo 19): Verificando modelos sin 'company_id'")
    _logger.info("    (Solo se consideran modelos pertenecientes a módulos instalados)")
    _logger.info("=====================================================================")

    # Usamos el entorno recibido directamente
    installed_modules = env['ir.module.module'].search([('state', '=', 'installed')])
    installed_module_names = set(installed_modules.mapped('name'))
    all_models = env['ir.model'].search([])
    models_without_company_id = []
    for model_record in all_models:
        model_name = model_record.model
        module_name = model_record._module
        if module_name not in installed_module_names:
            continue
        try:
            model_class = env[model_name]
        except KeyError:
            continue
        if 'company_id' not in model_class._fields:
            if model_name.startswith('ir.') or \
                model_name.startswith('res.country') or \
                model_name.startswith('bus.') or \
                model_name.startswith('mail.'):
                pass
            else:
                models_without_company_id.append(f"{model_name} (Módulo: {module_name})")
    if models_without_company_id:
        _logger.warning(
            f"⚠️ ¡ATENCIÓN! Se encontraron {len(models_without_company_id)} modelos de módulos instalados sin 'company_id'. "
            f"Considere si estos modelos necesitan segregación por compañía: "
        )
        for model_info in models_without_company_id:
            _logger.info(f"    - {model_info}")
    else:
        _logger.info(
            "✅ ¡Éxito! Todos los modelos principales de los módulos instalados parecen tener el campo 'company_id'.")
    _logger.info("=====================================================================")
