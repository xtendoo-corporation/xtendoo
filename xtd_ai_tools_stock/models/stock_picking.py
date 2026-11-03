from odoo import models

from odoo.addons.xtd_ai.tools import check_draft_only, is_unlocked, unlocked_record

# confirmed cards whose own effects create and confirm transfers (§6.5): the
# deliveries of a sales order, the receipts of a purchase order
_PARENT_UNLOCKS = (
    ("sale.order", "action_confirm", "sale_id"),
    ("purchase.order", "button_confirm", "purchase_id"),
)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _xtd_ai_guard(self, unlockable=None, parent=False):
        if not self or not self.env.context.get("xtd_ai_run"):
            return  # nothing to guard on an empty recordset (Odoo calls it internally)
        if unlockable and len(self) == 1 and is_unlocked(self, unlockable):
            return
        if parent and self._xtd_ai_parent_unlocked():
            return
        check_draft_only(
            self.env,
            self.env._(
                "El agente IA no puede confirmar, reservar, validar ni borrar "
                "albaranes: "
                "lo hace una persona."
            ),
        )

    def _xtd_ai_parent_unlocked(self):
        """Transfers that the confirmed sale or purchase order of the running
        card creates: linked to that order, or new (draft) ones of its chain."""
        for model, method, field in _PARENT_UNLOCKS:
            target = unlocked_record(self.env, method)
            if not target or target[0] != model:
                continue
            linked = field in self._fields
            return all(
                (linked and picking[field].id == target[1]) or picking.state == "draft"
                for picking in self
            )
        return False

    def button_validate(self):
        self._xtd_ai_guard("button_validate")
        return super().button_validate()

    def action_confirm(self):
        self._xtd_ai_guard(parent=True)
        return super().action_confirm()

    def action_assign(self):
        self._xtd_ai_guard(parent=True)
        return super().action_assign()

    def _action_done(self):
        self._xtd_ai_guard("button_validate")
        return super()._action_done()

    def unlink(self):
        self._xtd_ai_guard()
        return super().unlink()
