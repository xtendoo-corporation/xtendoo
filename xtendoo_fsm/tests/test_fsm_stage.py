# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestFSMStage(TransactionCase):
    def test_stage_creation_and_order_count(self):
        stage = self.env['fsm.stage'].create({
            'name': 'En Proceso',
            'code': 'in_process',
            'sequence': 5,
            'color': '#FFD700',
        })
        partner = self.env['res.partner'].create({'name': 'Cliente Test'})

        self.env['fsm.order'].create({
            'partner_id': partner.id,
            'stage_id': stage.id,
            'description': 'Orden 1',
        })
        self.env['fsm.order'].create({
            'partner_id': partner.id,
            'stage_id': stage.id,
            'description': 'Orden 2',
        })

        self.assertEqual(stage.code, 'in_process')
        self.assertEqual(stage.order_count, 2)

    def test_default_stage_is_unique_per_company(self):
        stage1 = self.env['fsm.stage'].create({
            'name': 'Etapa 1',
            'code': 'stage1',
            'is_default': True,
        })
        stage2 = self.env['fsm.stage'].create({
            'name': 'Etapa 2',
            'code': 'stage2',
            'is_default': True,
        })

        stage1.invalidate_recordset()
        self.assertFalse(stage1.is_default)
        self.assertTrue(stage2.is_default)

    def test_stage_code_validation(self):
        with self.assertRaises(ValidationError):
            self.env['fsm.stage'].create({
                'name': 'Código inválido',
                'code': 'bad code!',
            })
