# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from . import models
from . import wizard


def post_init_hook(env):
    """Hook ejecutado después de la instalación del módulo"""
    # Asignar grupos FSM a todos los usuarios internos
    try:
        # Buscar los grupos FSM
        fsm_user_group = env.ref('xtendoo_fsm.group_fsm_user', raise_if_not_found=False)
        fsm_manager_group = env.ref('xtendoo_fsm.group_fsm_manager', raise_if_not_found=False)

        if fsm_user_group:
            # Buscar todos los usuarios internos activos (no portal, no público)
            internal_users = env['res.users'].search([
                ('active', '=', True),
                ('share', '=', False),  # Solo usuarios internos (no portal)
            ])

            if internal_users:
                # Asignar el grupo FSM Usuario a todos los usuarios internos
                for user in internal_users:
                    if fsm_user_group.id not in user.groups_id.ids:
                        user.groups_id = [(4, fsm_user_group.id)]

                # Asignar FSM Manager solo al admin
                admin_user = env['res.users'].search([('login', '=', 'admin')], limit=1)
                if admin_user and fsm_manager_group:
                    if fsm_manager_group.id not in admin_user.groups_id.ids:
                        admin_user.groups_id = [(4, fsm_manager_group.id)]

                env.cr.commit()
    except Exception as e:
        print(f"Error asignando grupos FSM: {e}")

    # Crear proyecto por defecto para servicios de campo si no existe
    company = env.company
    project = env['project.project'].search([
        ('is_fsm', '=', True),
        ('company_id', '=', company.id)
    ], limit=1)

    if not project:
        project = env['project.project'].create({
            'name': 'Servicios de Campo',
            'is_fsm': True,
            'allow_timesheets': True,
            'company_id': company.id,
        })

    # Crear etapas por defecto si no existen
    stages = [
        ('new', 'Nuevo', 1, False, '#E6E6FA'),
        ('scheduled', 'Programado', 2, False, '#87CEEB'),
        ('in_progress', 'En Progreso', 3, False, '#FFD700'),
        ('done', 'Completado', 4, True, '#90EE90'),
        ('cancelled', 'Cancelado', 5, True, '#FFB6C1'),
    ]

    for code, name, sequence, closed, color in stages:
        existing = env['fsm.stage'].search([
            ('code', '=', code),
            ('company_id', '=', company.id)
        ])
        if not existing:
            env['fsm.stage'].create({
                'name': name,
                'code': code,
                'sequence': sequence,
                'is_closed': closed,
                'color': color,
                'company_id': company.id,
            })
