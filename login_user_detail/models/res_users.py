# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Aysha Shalin (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
# Odoo 18: _check_credentials signature changed to (credential, env)
# where credential = {'type': 'password', 'login': str, 'password': str}
# and env = {'interactive': bool, ...}
import logging
from odoo.http import request
from odoo import models

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    """ Inherits 'res.users' to add custom functionality for logging the login
    details of user. """
    _inherit = 'res.users'

    def _check_credentials(self, credential, env):
        """Check user credentials during login and log the login details.

        Odoo 18: credential es un dict {'type', 'login', 'password'}.
        El método se llama sobre el registro del usuario autenticado (self),
        por lo que self.name devuelve correctamente el nombre del usuario.
        """
        result = super()._check_credentials(credential, env)
        # Registrar el acceso sólo tras autenticación exitosa
        ip_address = (
            request.httprequest.environ.get('REMOTE_ADDR', 'n/a')
            if request else 'n/a'
        )
        self.env['login.detail'].sudo().create({
            'name': self.name,
            'ip_address': ip_address,
        })
        return result
