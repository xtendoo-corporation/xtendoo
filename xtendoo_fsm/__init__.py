# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from . import models


def _post_init_hook(env):
    """Hook ejecutado después de la instalación del módulo"""
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
