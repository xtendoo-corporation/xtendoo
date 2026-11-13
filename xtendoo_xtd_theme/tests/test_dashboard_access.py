# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
from pathlib import Path

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged

MODULE_PATH = Path(__file__).resolve().parents[1]


# post_install: crear usuarios necesita el registro completo (otros módulos
# añaden columnas obligatorias a res.partner).
@tagged("post_install", "-at_install")
class TestXtdDashboardAccess(TransactionCase):
    """Permisos y saneado del dashboard con usuarios reales (no superusuario)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal = new_test_user(cls.env, login="xtd_dash_internal", groups="base.group_user")
        cls.other = new_test_user(cls.env, login="xtd_dash_other", groups="base.group_user")
        cls.portal = new_test_user(cls.env, login="xtd_dash_portal", groups="base.group_portal")
        cls.service = cls.env["xtd.dashboard.service"]
        cls.global_block_ids = [
            block["block_id"] for block in cls.service.get_dashboard_layout()["blocks"]
        ]

    def _custom_block(self):
        return self.env["xtd.dashboard.block"].create({
            "name": "Contactos",
            "technical_key": "custom_res_partner_access_test",
            "block_type": "list",
            "component": "generic_list",
            "model_name": "res.partner",
            "config": {"fields": ["display_name"], "limit": 5},
        })

    def test_internal_user_cannot_edit_global_layout(self):
        layout = self.service.with_user(self.internal).get_dashboard_layout()

        self.assertEqual(layout["mode"], "global")
        self.assertFalse(layout["can_edit"])

    def test_internal_user_can_start_custom_dashboard(self):
        """Con el dashboard personalizado activado y sin líneas propias el
        usuario ve el diseño global, pero tiene que poder editarlo."""
        self.internal.xtd_use_custom_dashboard = True
        service = self.service.with_user(self.internal)

        layout = service.get_dashboard_layout()

        self.assertEqual(layout["mode"], "user")
        self.assertTrue(layout["can_edit"])
        self.assertTrue(layout["can_customize"])
        self.assertEqual([b["block_id"] for b in layout["blocks"]], self.global_block_ids)

    def test_internal_user_saves_own_layout_without_touching_global(self):
        self.internal.xtd_use_custom_dashboard = True
        service = self.service.with_user(self.internal)
        blocks = list(reversed(service.get_dashboard_layout()["blocks"]))

        saved = service.save_dashboard_layout(blocks)

        self.assertEqual(
            [b["block_id"] for b in saved["blocks"]],
            list(reversed(self.global_block_ids)),
        )
        own_lines = self.env["xtd.dashboard.user.layout"].search([
            ("user_id", "=", self.internal.id),
        ])
        self.assertEqual(len(own_lines), len(self.global_block_ids))
        # El diseño global y el de otro usuario siguen igual.
        self.assertEqual(
            [b["block_id"] for b in self.service.get_dashboard_layout()["blocks"]],
            self.global_block_ids,
        )
        self.assertFalse(self.env["xtd.dashboard.user.layout"].search([
            ("user_id", "=", self.other.id),
        ]))

    def test_internal_user_without_custom_flag_cannot_save(self):
        service = self.service.with_user(self.internal)
        blocks = list(reversed(service.get_dashboard_layout()["blocks"]))

        service.save_dashboard_layout(blocks)

        self.assertEqual(
            [b["block_id"] for b in self.service.get_dashboard_layout()["blocks"]],
            self.global_block_ids,
        )

    def test_portal_user_cannot_change_dashboard(self):
        self.portal.sudo().res_users_settings_id  # asegura que existe el registro de ajustes
        service = self.service.with_user(self.portal)

        with self.assertRaises(AccessError):
            service.save_dashboard_layout([{"block_id": self.global_block_ids[0]}])
        with self.assertRaises(AccessError):
            service.delete_custom_block(self.global_block_ids[0])

    def test_save_ignores_invalid_blocks_and_sizes(self):
        blocks = [
            {"block_id": self.global_block_ids[0], "size": "enorme"},
            {"block_id": 999999999, "size": "small"},
            {"block_id": self.global_block_ids[0], "size": "small"},  # repetido
            {"block_id": self.global_block_ids[1], "size": "large"},
        ]

        saved = self.service.save_dashboard_layout(blocks)

        self.assertEqual(
            [(b["block_id"], b["size"]) for b in saved["blocks"]],
            [(self.global_block_ids[0], "medium"), (self.global_block_ids[1], "large")],
        )

    def test_save_does_not_freeze_block_config_in_layout_line(self):
        """El cliente devuelve la configuración fusionada: en la línea solo se
        guarda lo que el usuario decide (oculto o no)."""
        block = self._custom_block()
        line = self.env["xtd.dashboard.layout"].create({"block_id": block.id})
        blocks = self.service.get_dashboard_layout()["blocks"]
        sent = next(b for b in blocks if b["block_id"] == block.id)
        self.assertIn("field_labels", sent["config"])
        sent["config"]["hidden"] = True
        sent["config"]["domain"] = [("id", ">", 0)]

        self.service.save_dashboard_layout(blocks)

        self.assertEqual(line.config, {"hidden": True})
        # Un cambio posterior del bloque se sigue viendo.
        block.config = {"fields": ["display_name"], "limit": 9}
        updated = next(
            b for b in self.service.get_dashboard_layout()["blocks"] if b["block_id"] == block.id
        )
        self.assertEqual(updated["config"]["limit"], 9)
        self.assertNotIn("domain", updated["config"])

    def test_non_admin_delete_only_removes_own_line(self):
        block = self._custom_block()
        self.env["xtd.dashboard.layout"].create({"block_id": block.id})
        self.internal.xtd_use_custom_dashboard = True
        own_line = self.env["xtd.dashboard.user.layout"].create({
            "block_id": block.id,
            "user_id": self.internal.id,
        })
        other_line = self.env["xtd.dashboard.user.layout"].create({
            "block_id": block.id,
            "user_id": self.other.id,
        })

        self.service.with_user(self.internal).delete_custom_block(block.id)

        self.assertTrue(block.exists(), "Un usuario normal no puede borrar un bloque global")
        self.assertFalse(own_line.exists())
        self.assertTrue(other_line.exists())
        self.assertTrue(self.env["xtd.dashboard.layout"].search([("block_id", "=", block.id)]))

    def test_default_layout_data_survives_module_updates(self):
        """El diseño global se guarda sobre los registros de datos: tienen que
        ir en noupdate y no redefinirse en otro fichero."""
        root = ET.parse(MODULE_PATH / "data" / "xtd_dashboard_blocks.xml").getroot()
        layout_records = root.findall(".//record[@model='xtd.dashboard.layout']")
        protected = root.findall("./data[@noupdate='1']/record[@model='xtd.dashboard.layout']")
        self.assertTrue(layout_records)
        self.assertEqual(len(layout_records), len(protected))

        for name in ("xtd_dashboard_disable_default_blocks.xml", "xtd_dashboard_available_blocks.xml"):
            other = ET.parse(MODULE_PATH / "data" / name).getroot()
            self.assertFalse(
                other.findall(".//record[@model='xtd.dashboard.layout']"),
                f"{name} no debe tocar el diseño por defecto",
            )

    def test_activities_block_uses_current_user_and_real_action(self):
        js = (MODULE_PATH / "static/src/components/dashboard/dashboard.js").read_text(encoding="utf-8")
        xml = (MODULE_PATH / "static/src/components/dashboard/dashboard.xml").read_text(encoding="utf-8")

        self.assertIn('[["user_id", "=", user.userId]]', js)
        self.assertNotIn("this.session.uid", js)
        self.assertIn("openAction('mail.mail_activity_action')", xml)
        self.assertNotIn("mail_activity_action_view_tree", xml)
        if "mail.activity" in self.env:
            action = self.env.ref("mail.mail_activity_action")
            self.assertEqual(action._name, "ir.actions.act_window")
