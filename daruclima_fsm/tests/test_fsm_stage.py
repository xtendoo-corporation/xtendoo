# Copyright 2025 Xtendoo Software SLU
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError


class TestFSMStage(TransactionCase):
    """Test cases for FSM Stage functionality"""

    def setUp(self):
        super(TestFSMStage, self).setUp()

        # Create test company
        self.company = self.env['res.company'].create({
            'name': 'Test Company',
        })

    def test_stage_creation(self):
        """Test FSM stage creation"""
        stage = self.env['daruclima.fsm.stage'].create({
            'name': 'New Stage',
            'code': 'new_stage',
            'sequence': 10,
            'is_default': False,
            'is_closed': False,
            'color': '#FF5733',
        })

        self.assertEqual(stage.name, 'New Stage')
        self.assertEqual(stage.code, 'new_stage')
        self.assertEqual(stage.sequence, 10)
        self.assertFalse(stage.is_default)
        self.assertFalse(stage.is_closed)
        self.assertEqual(stage.color, '#FF5733')

    def test_default_stage(self):
        """Test default stage functionality"""
        # Create a default stage
        default_stage = self.env['daruclima.fsm.stage'].create({
            'name': 'Default Stage',
            'code': 'default',
            'sequence': 1,
            'is_default': True,
            'is_closed': False,
            'color': '#00FF00',
        })

        # Create a non-default stage
        regular_stage = self.env['daruclima.fsm.stage'].create({
            'name': 'Regular Stage',
            'code': 'regular',
            'sequence': 2,
            'is_default': False,
            'is_closed': False,
            'color': '#0000FF',
        })

        # Test that we can identify default stages
        self.assertTrue(default_stage.is_default)
        self.assertFalse(regular_stage.is_default)

    def test_closed_stage(self):
        """Test closed stage functionality"""
        closed_stage = self.env['daruclima.fsm.stage'].create({
            'name': 'Completed',
            'code': 'done',
            'sequence': 100,
            'is_default': False,
            'is_closed': True,
            'color': '#90EE90',
        })

        self.assertTrue(closed_stage.is_closed)

    def test_stage_sequence(self):
        """Test stage ordering by sequence"""
        stage1 = self.env['daruclima.fsm.stage'].create({
            'name': 'Stage 1',
            'code': 'stage1',
            'sequence': 10,
        })

        stage2 = self.env['daruclima.fsm.stage'].create({
            'name': 'Stage 2',
            'code': 'stage2',
            'sequence': 5,
        })

        stage3 = self.env['daruclima.fsm.stage'].create({
            'name': 'Stage 3',
            'code': 'stage3',
            'sequence': 15,
        })

        # Get stages ordered by sequence
        stages = self.env['daruclima.fsm.stage'].search([
            ('id', 'in', [stage1.id, stage2.id, stage3.id])
        ], order='sequence')

        self.assertEqual(stages[0], stage2)  # sequence 5
        self.assertEqual(stages[1], stage1)  # sequence 10
        self.assertEqual(stages[2], stage3)  # sequence 15

    def test_stage_company_filter(self):
        """Test stage filtering by company"""
        stage_company1 = self.env['daruclima.fsm.stage'].create({
            'name': 'Stage Company 1',
            'code': 'comp1',
            'sequence': 1,
            'company_id': self.company.id,
        })

        stage_global = self.env['daruclima.fsm.stage'].create({
            'name': 'Global Stage',
            'code': 'global',
            'sequence': 2,
            'company_id': False,
        })

        # Both stages should be available for the company
        company_stages = self.env['daruclima.fsm.stage'].search([
            ('company_id', 'in', [self.company.id, False])
        ])

        self.assertIn(stage_company1, company_stages)
        self.assertIn(stage_global, company_stages)

    def test_stage_color_validation(self):
        """Test that color field accepts valid hex colors"""
        stage = self.env['daruclima.fsm.stage'].create({
            'name': 'Colored Stage',
            'code': 'colored',
            'sequence': 1,
            'color': '#ABCDEF',
        })

        self.assertEqual(stage.color, '#ABCDEF')


class TestDaruclimeFSMStage(TransactionCase):
    """Test cases para etapas FSM"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({
            'name': 'Cliente Test',
        })

        cls.team = cls.env['daruclima.fsm.team'].create({
            'name': 'Equipo Test',
            'code': 'TEST',
        })

    def test_stage_creation(self):
        """Test creación de etapas FSM"""
        stage = self.env['daruclima.fsm.stage'].create({
            'name': 'En Proceso',
            'code': 'in_process',
            'sequence': 5,
            'color': '#FFD700',
            'description': 'Trabajo en progreso',
        })

        self.assertEqual(stage.name, 'En Proceso')
        self.assertEqual(stage.code, 'in_process')
        self.assertEqual(stage.sequence, 5)
        self.assertEqual(stage.color, '#FFD700')
        self.assertFalse(stage.is_closed)
        self.assertFalse(stage.is_default)
        self.assertTrue(stage.active)

    def test_stage_default_validation(self):
        """Test validación de etapa por defecto"""
        # Crear primera etapa por defecto
        stage1 = self.env['daruclima.fsm.stage'].create({
            'name': 'Etapa 1',
            'code': 'stage1',
            'is_default': True,
        })

        self.assertTrue(stage1.is_default)

        # Crear segunda etapa por defecto
        stage2 = self.env['daruclima.fsm.stage'].create({
            'name': 'Etapa 2',
            'code': 'stage2',
            'is_default': True,
        })

        # Verificar que solo una puede ser por defecto
        stage1.refresh()
        self.assertFalse(stage1.is_default)
        self.assertTrue(stage2.is_default)

    def test_stage_order_count(self):
        """Test conteo de órdenes por etapa"""
        stage = self.env['daruclima.fsm.stage'].create({
            'name': 'Etapa Test',
            'code': 'test_stage',
        })

        # Crear órdenes en esta etapa
        self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'team_id': self.team.id,
            'stage_id': stage.id,
            'description': 'Orden 1',
        })

        self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'team_id': self.team.id,
            'stage_id': stage.id,
            'description': 'Orden 2',
        })

        # Verificar conteo
        self.assertEqual(stage.order_count, 2)

    def test_stage_closed_functionality(self):
        """Test funcionalidad de etapas cerradas"""
        closed_stage = self.env['daruclima.fsm.stage'].create({
            'name': 'Completado',
            'code': 'completed',
            'is_closed': True,
        })

        order = self.env['daruclima.fsm.order'].create({
            'partner_id': self.partner.id,
            'team_id': self.team.id,
            'stage_id': closed_stage.id,
            'description': 'Orden completada',
        })

        # Verificar que la orden se marca como cerrada
        self.assertTrue(order.is_closed)

    def test_stage_required_fields(self):
        """Test campos requeridos de etapas"""
        with self.assertRaises(ValidationError):
            self.env['daruclima.fsm.stage'].create({
                'code': 'test',
            })

        with self.assertRaises(ValidationError):
            self.env['daruclima.fsm.stage'].create({
                'name': 'Etapa sin código',
            })

    def test_stage_write_default_validation(self):
        """Test validación al escribir etapa por defecto"""
        stage1 = self.env['daruclima.fsm.stage'].create({
            'name': 'Etapa 1',
            'code': 'stage1',
            'is_default': True,
        })

        stage2 = self.env['daruclima.fsm.stage'].create({
            'name': 'Etapa 2',
            'code': 'stage2',
            'is_default': False,
        })

        # Cambiar la segunda etapa a por defecto
        stage2.write({'is_default': True})

        # Verificar que la primera ya no es por defecto
        stage1.refresh()
        self.assertFalse(stage1.is_default)
        self.assertTrue(stage2.is_default)
