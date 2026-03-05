# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, tagged, new_test_user

import logging

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestCrmMultiCompanyEncapsulation(TransactionCase):
    """Tests para verificar el aislamiento multi-compañía en CRM.

    Escenarios cubiertos:
    ─────────────────────
    1. Un usuario solo ve oportunidades de su compañía activa.
    2. Un usuario NO ve oportunidades de otra compañía.
    3. Leads sin compañía (company_id=False) son visibles por todos.
    4. Un usuario con see_all_companies=True ve todo.
    5. Al crear un lead, se asigna automáticamente la compañía activa.
    6. Los equipos CRM se filtran por compañía activa.
    7. Al cambiar de compañía, cambian los leads visibles.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Compañías ──
        cls.company_a = cls.env.ref("base.main_company")

        # Crear segunda compañía: desactivar _check_company temporalmente
        # porque stock.warehouse.create() falla con las reglas de encapsulación
        from odoo import models as _models

        original_check = _models.BaseModel._check_company
        _models.BaseModel._check_company = lambda self, *a, **kw: None
        try:
            cls.company_b = (
                cls.env["res.company"]
                .sudo()
                .with_context(mail_create_nolog=True, no_reset_password=True)
                .create({"name": "Test CRM Company B"})
            )
        finally:
            _models.BaseModel._check_company = original_check

        # ── Usuarios ──
        cls.user_a = new_test_user(
            cls.env,
            login="test_crm_user_a",
            groups="sales_team.group_sale_salesman_all_leads",
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id, cls.company_b.id])],
        )
        cls.user_a.see_all_companies = False

        cls.user_b = new_test_user(
            cls.env,
            login="test_crm_user_b",
            groups="sales_team.group_sale_salesman_all_leads",
            company_id=cls.company_b.id,
            company_ids=[(6, 0, [cls.company_b.id])],
        )
        cls.user_b.see_all_companies = False

        cls.user_admin_all = new_test_user(
            cls.env,
            login="test_crm_user_admin",
            groups="sales_team.group_sale_salesman_all_leads",
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id, cls.company_b.id])],
        )
        cls.user_admin_all.see_all_companies = True

        # ── Equipos CRM ──
        CrmTeam = cls.env["crm.team"].sudo()
        cls.team_a = CrmTeam.create(
            {
                "name": "Test CRM Equipo A",
                "company_id": cls.company_a.id,
            }
        )
        cls.team_b = CrmTeam.create(
            {
                "name": "Test CRM Equipo B",
                "company_id": cls.company_b.id,
            }
        )
        cls.team_shared = CrmTeam.create(
            {
                "name": "Test CRM Equipo Compartido",
                "company_id": False,
            }
        )

        # ── Leads / Oportunidades ──
        CrmLead = cls.env["crm.lead"].sudo()
        cls.lead_a1 = CrmLead.create(
            {
                "name": "Test CRM Oport A-1",
                "company_id": cls.company_a.id,
                "team_id": cls.team_a.id,
                "type": "opportunity",
            }
        )
        cls.lead_a2 = CrmLead.create(
            {
                "name": "Test CRM Oport A-2",
                "company_id": cls.company_a.id,
                "team_id": cls.team_a.id,
                "type": "opportunity",
            }
        )
        cls.lead_b1 = CrmLead.create(
            {
                "name": "Test CRM Oport B-1",
                "company_id": cls.company_b.id,
                "team_id": cls.team_b.id,
                "type": "opportunity",
            }
        )
        cls.lead_no_company = CrmLead.create(
            {
                "name": "Test CRM Oport Sin Company",
                "company_id": False,
                "team_id": cls.team_shared.id,
                "type": "opportunity",
            }
        )

    # ─────────────────────────────────────────────────────────
    # Test 1: Usuario ve solo leads de su compañía activa
    # ─────────────────────────────────────────────────────────
    def test_01_user_sees_own_company_leads(self):
        """user_a (company activa = A) debe ver leads de Company A y sin compañía."""
        leads = (
            self.env["crm.lead"]
            .with_user(self.user_a)
            .with_context(allowed_company_ids=[self.company_a.id])
            .search([])
        )
        lead_ids = leads.ids

        self.assertIn(
            self.lead_a1.id,
            lead_ids,
            "user_a debería ver Oportunidad A-1 (misma compañía)",
        )
        self.assertIn(
            self.lead_a2.id,
            lead_ids,
            "user_a debería ver Oportunidad A-2 (misma compañía)",
        )
        self.assertIn(
            self.lead_no_company.id, lead_ids, "user_a debería ver el lead sin compañía"
        )

    # ─────────────────────────────────────────────────────────
    # Test 2: Usuario NO ve leads de otra compañía
    # ─────────────────────────────────────────────────────────
    def test_02_user_does_not_see_other_company_leads(self):
        """user_a (company activa = A) NO debe ver leads de Company B."""
        leads = (
            self.env["crm.lead"]
            .with_user(self.user_a)
            .with_context(allowed_company_ids=[self.company_a.id])
            .search([])
        )
        lead_ids = leads.ids

        self.assertNotIn(
            self.lead_b1.id,
            lead_ids,
            "user_a NO debería ver Oportunidad B-1 (otra compañía)",
        )

    # ─────────────────────────────────────────────────────────
    # Test 3: User B solo ve leads de Company B
    # ─────────────────────────────────────────────────────────
    def test_03_user_b_sees_company_b_leads(self):
        """user_b (company activa = B) debe ver leads de Company B."""
        leads = (
            self.env["crm.lead"]
            .with_user(self.user_b)
            .with_context(allowed_company_ids=[self.company_b.id])
            .search([])
        )
        lead_ids = leads.ids

        self.assertIn(self.lead_b1.id, lead_ids, "user_b debería ver Oportunidad B-1")
        self.assertNotIn(
            self.lead_a1.id, lead_ids, "user_b NO debería ver Oportunidad A-1"
        )
        self.assertNotIn(
            self.lead_a2.id, lead_ids, "user_b NO debería ver Oportunidad A-2"
        )

    # ─────────────────────────────────────────────────────────
    # Test 4: see_all_companies bypass ve todo
    # ─────────────────────────────────────────────────────────
    def test_04_see_all_companies_bypasses_filter(self):
        """user_admin_all (see_all_companies=True) debe ver TODOS los leads."""
        leads = (
            self.env["crm.lead"]
            .with_user(self.user_admin_all)
            .with_context(allowed_company_ids=[self.company_a.id])
            .search([])
        )
        lead_ids = leads.ids

        self.assertIn(self.lead_a1.id, lead_ids, "Admin debería ver Oportunidad A-1")
        self.assertIn(self.lead_b1.id, lead_ids, "Admin debería ver Oportunidad B-1")
        self.assertIn(
            self.lead_no_company.id, lead_ids, "Admin debería ver el lead sin compañía"
        )

    # ─────────────────────────────────────────────────────────
    # Test 5: Crear lead asigna compañía automáticamente
    # ─────────────────────────────────────────────────────────
    def test_05_create_lead_assigns_company(self):
        """Al crear un lead sin company_id, se asigna la compañía activa."""
        lead = (
            self.env["crm.lead"]
            .with_user(self.user_a)
            .with_context(allowed_company_ids=[self.company_a.id])
            .create(
                {
                    "name": "Test Nuevo Lead Auto-Company",
                    "type": "opportunity",
                }
            )
        )
        self.assertEqual(
            lead.company_id.id,
            self.company_a.id,
            "El lead creado debería tener company_id = Company A",
        )

    # ─────────────────────────────────────────────────────────
    # Test 6: Equipos CRM se filtran por compañía
    # ─────────────────────────────────────────────────────────
    def test_06_crm_teams_filtered_by_company(self):
        """user_a debe ver solo equipos de Company A y los compartidos."""
        teams = (
            self.env["crm.team"]
            .with_user(self.user_a)
            .with_context(allowed_company_ids=[self.company_a.id])
            .search([])
        )
        team_ids = teams.ids

        self.assertIn(self.team_a.id, team_ids, "user_a debería ver Equipo A")
        self.assertIn(
            self.team_shared.id, team_ids, "user_a debería ver Equipo Compartido"
        )
        self.assertNotIn(self.team_b.id, team_ids, "user_a NO debería ver Equipo B")

    # ─────────────────────────────────────────────────────────
    # Test 7: Cambio de compañía cambia leads visibles
    # ─────────────────────────────────────────────────────────
    def test_07_switching_company_changes_visible_leads(self):
        """Al cambiar la compañía por defecto del usuario, cambian los leads visibles.

        Nota: user.company_id en ir.rule se refiere a la compañía por defecto del
        usuario, NO al allowed_company_ids del contexto.
        """
        # Con Company A como default
        leads_a = (
            self.env["crm.lead"]
            .with_user(self.user_a)
            .with_context(allowed_company_ids=[self.company_a.id])
            .search([])
        )
        self.assertIn(self.lead_a1.id, leads_a.ids)
        self.assertNotIn(self.lead_b1.id, leads_a.ids)

        # Cambiar la compañía por defecto del usuario a Company B
        self.user_a.company_id = self.company_b
        leads_b = (
            self.env["crm.lead"]
            .with_user(self.user_a)
            .with_context(allowed_company_ids=[self.company_b.id])
            .search([])
        )
        self.assertIn(
            self.lead_b1.id,
            leads_b.ids,
            "Tras cambiar company por defecto a B, debería ver lead B-1",
        )
        self.assertNotIn(
            self.lead_a1.id,
            leads_b.ids,
            "Tras cambiar company por defecto a B, NO debería ver lead A-1",
        )
        # Restaurar
        self.user_a.company_id = self.company_a

    # ─────────────────────────────────────────────────────────
    # Test 8: Lead sin compañía visible desde cualquier compañía
    # ─────────────────────────────────────────────────────────
    def test_08_no_company_lead_visible_everywhere(self):
        """Leads con company_id=False son visibles para cualquier usuario."""
        # Visible desde user_a (company default = A)
        leads_a = (
            self.env["crm.lead"]
            .with_user(self.user_a)
            .with_context(allowed_company_ids=[self.company_a.id])
            .search([("id", "=", self.lead_no_company.id)])
        )
        self.assertTrue(leads_a, "Lead sin compañía debería ser visible para user_a")

        # Visible desde user_admin_all (bypass)
        leads_admin = (
            self.env["crm.lead"]
            .with_user(self.user_admin_all)
            .with_context(allowed_company_ids=[self.company_b.id])
            .search([("id", "=", self.lead_no_company.id)])
        )
        self.assertTrue(leads_admin, "Lead sin compañía debería ser visible para admin")
