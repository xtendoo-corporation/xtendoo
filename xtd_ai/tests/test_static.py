import os
import re

from odoo import addons
from odoo.tests import TransactionCase, tagged

_SUDO = re.compile(r"\bsudo\s*\(")


def addon_dirs(prefix):
    """Every addon directory named ``prefix*`` on the addons path."""
    found = {}
    for path in addons.__path__:
        if not os.path.isdir(path):
            continue
        for name in os.listdir(path):
            if name.startswith(prefix) and os.path.isfile(
                os.path.join(path, name, "__manifest__.py")
            ):
                found[name] = os.path.join(path, name)
    return found


def sudo_offenders(path, name):
    offenders = []
    for root, _dirs, files in os.walk(path):
        for filename in files:
            if not filename.endswith((".py", ".xml", ".csv")):
                continue
            full = os.path.join(root, filename)
            with open(full, encoding="utf-8") as handle:
                for number, line in enumerate(handle, 1):
                    code = line.split("#", 1)[0] if filename.endswith(".py") else line
                    if _SUDO.search(code):
                        offenders.append(
                            f"{name}/{os.path.relpath(full, path)}:{number}"
                        )
    return offenders


@tagged("post_install", "-at_install")
class TestStatic(TransactionCase):
    def test_no_sudo_in_tools_modules(self):
        """Tool modules (xtd_ai_tools_*) must never call sudo() (CONTRACT §6)."""
        offenders = []
        for name, path in addon_dirs("xtd_ai_tools_").items():
            offenders += sudo_offenders(path, name)
        self.assertFalse(
            offenders, f"sudo() is forbidden in AI tool modules: {offenders}"
        )

    def test_scanner_detects_sudo(self):
        self.assertTrue(_SUDO.search("self.env['x'].sudo().search([])"))
        self.assertTrue(_SUDO.search("rec.sudo ()"))
        self.assertFalse(_SUDO.search("pseudo(1)"))

    def test_scanner_finds_the_gateway(self):
        found = addon_dirs("xtd_ai")
        self.assertIn("xtd_ai", found)
        # the gateway itself is allowed to use sudo (commented), the scanner must see it
        self.assertTrue(sudo_offenders(found["xtd_ai"], "xtd_ai"))
