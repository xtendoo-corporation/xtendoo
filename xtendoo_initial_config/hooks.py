# python
def post_init_hook(env):
    print("*"*80)
    """Script post-instalación"""
    # Buscar el idioma español
    lang_es = env['res.lang'].search([('code', '=', 'es_ES')], limit=1)
    if lang_es:
        wizard = env['base.language.install'].create({'lang_ids': [(6, 0, [lang_es.id])], 'overwrite': True})
        wizard.lang_install()

    # Instalar y activar el idioma español si no está activo
    lang_es = env['res.lang'].search([('code', '=', 'es_ES')], limit=1)

    print("Activating Spanish language...")
    # Verificar si el idioma español ya existe y está activo
    print("lang_es:", lang_es)
    print("lang_es.active:", lang_es.active)

    if not lang_es or not lang_es.active:
        # Si no existe o no está activo, instalar y activar
        wizard = env['base.language.install'].create({'lang': 'es_ES'})
        wizard.lang_install()
        lang_es = env['res.lang'].search([('code', '=', 'es_ES')], limit=1)
        if lang_es:
            lang_es.active = True

    # Instalar módulos requeridos, evitando conflicto entre web_responsive y web_enterprise
    installed_modules = env['ir.module.module'].search([('state', '=', 'installed')]).mapped('name')
    for module in ['l10n_es_toponyms', 'web_responsive', 'contacts']:
        if module == 'web_responsive' and 'web_enterprise' in installed_modules:
            continue  # Saltar instalación si web_enterprise está instalado
        mod = env['ir.module.module'].search([('name', '=', module)])
        if mod and mod.state != 'installed':
            mod.button_install()

    # Configurar idioma español para todos los usuarios
    env['res.users'].set_spanish_language_for_all()

    # Desinstalar el idioma inglés
    try:
        english_lang = env['res.lang'].search([('code', '=', 'en_US')])
        if english_lang:
            if env['ir.config_parameter'].get_param('base.lang_default') != 'en_US':
                english_lang.active = False
    except Exception as e:
        env.cr.rollback()
