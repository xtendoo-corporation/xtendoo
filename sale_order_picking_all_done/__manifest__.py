# -*- coding: utf-8 -*-

###################################################################################
#
#    Xtendoo Technologies
#    Copyright (C) 2018-TODAY Xtendoo Technologies (<https://www.xtendoo.com>).
#    Author: Manuel Calero Solís(<https://www.xtendoo.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################

{
    'name': 'Sale Order Picking All Done',
    'summary': """Sale Order Picking All Done""",
    'version': '12.0.1.0.0',
    'description': """Sale Order Picking All Done""",
    'author': 'Manuel Calero Solís',
    'company': 'Xtendoo',
    'website': 'http://www.xtendoo.com',
    'category': 'Extra Tools',
    'depends': [
        'stock',
        'sale'
    ],
    'license': 'AGPL-3',
    'data': [
        'views/views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
