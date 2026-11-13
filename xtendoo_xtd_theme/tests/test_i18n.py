# -*- coding: utf-8 -*-

import re
from pathlib import Path

from odoo.tests import TransactionCase
import polib

MODULE_PATH = Path(__file__).resolve().parents[1]
I18N = MODULE_PATH / "i18n"


def _read(path):
    """{msgid: msgstr} de un .po/.pot. polib es el lector que usa Odoo: si el
    fichero no se puede leer, tampoco se podría cargar."""
    return {entry.msgid: entry.msgstr for entry in polib.pofile(str(path)) if entry.msgid}


class TestXtdI18n(TransactionCase):
    def test_spanish_translation_loads_and_covers_user_facing_english(self):
        translations = _read(I18N / "es.po")

        for source, expected in {
            "Dark": "Oscuro",
            "Light": "Claro",
            "System": "Sistema",
            "Theme": "Tema",
            "Xtd Error": "Error de Xtd",
            "Manage Xtd Databases": "Gestionar bases de datos de Xtd",
            "Only internal users can change the dashboard.": (
                "Solo los usuarios internos pueden modificar el dashboard."
            ),
        }.items():
            with self.subTest(source=source):
                self.assertEqual(translations.get(source), expected)

    def test_translation_has_no_stale_entries(self):
        template = _read(I18N / "xtendoo_xtd_theme.pot")
        translated = {src for src, value in _read(I18N / "es.po").items() if value}

        self.assertFalse(translated - set(template), "es.po tiene entradas que ya no existen en el .pot")

    def test_template_attributes_have_no_untranslatable_literals(self):
        """Un ternario con textos dentro de t-att-title no lo recoge el
        exportador de traducciones: los textos pasan por un getter con _t."""
        pattern = re.compile(r'''t-att-(?:title|placeholder|aria-label|alt)="([^"]*)"''')
        for path in (MODULE_PATH / "static/src").rglob("*.xml"):
            for value in pattern.findall(path.read_text(encoding="utf-8")):
                with self.subTest(file=path.name, value=value):
                    self.assertNotIn("'", value)

    def test_visible_defaults_in_dashboard_js_go_through_translation(self):
        js = (MODULE_PATH / "static/src/components/dashboard/dashboard.js").read_text(encoding="utf-8")

        for label in ("Pedidos venta", "Presupuestos", "Pedidos de compra", "Facturado (mes)"):
            with self.subTest(label=label):
                self.assertIn(f'_t("{label}")', js)
                self.assertNotIn(f'|| "{label}"', js)
