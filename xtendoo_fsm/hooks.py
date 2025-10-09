# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

def assign_fsm_groups_to_admin(env):
    """Asignar grupos FSM al usuario administrador"""
    try:
        # Buscar el usuario admin
        admin_user = env['res.users'].search([('login', '=', 'admin')], limit=1)
        if not admin_user:
            # Si no existe admin, buscar el primer usuario activo
            admin_user = env['res.users'].search([('active', '=', True)], limit=1)

        if admin_user:
            # Buscar los grupos FSM
            fsm_user_group = env.ref('xtendoo_fsm.group_fsm_user', raise_if_not_found=False)
            fsm_manager_group = env.ref('xtendoo_fsm.group_fsm_manager', raise_if_not_found=False)

            if fsm_user_group and fsm_manager_group:
                # Asignar los grupos al usuario
                admin_user.groups_id = [(4, fsm_user_group.id), (4, fsm_manager_group.id)]
                env.cr.commit()
                return True
    except Exception as e:
        print(f"Error asignando grupos FSM: {e}")
        return False
    return False
