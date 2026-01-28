# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class PosCashCalculatorWizard(models.TransientModel):
    _name = "pos.cash.calculator.wizard"
    _description = "Calculadora de Monedas y Billetes"

    # Billetes
    qty_200 = fields.Integer(string="Cantidad 200€", default=0)
    qty_100 = fields.Integer(string="Cantidad 100€", default=0)
    qty_50 = fields.Integer(string="Cantidad 50€", default=0)
    qty_20 = fields.Integer(string="Cantidad 20€", default=0)
    qty_10 = fields.Integer(string="Cantidad 10€", default=0)
    qty_5 = fields.Integer(string="Cantidad 5€", default=0)

    # Monedas
    qty_2 = fields.Integer(string="Cantidad 2€", default=0)
    qty_1 = fields.Integer(string="Cantidad 1€", default=0)
    qty_050 = fields.Integer(string="Cantidad 0,50€", default=0)
    qty_025 = fields.Integer(string="Cantidad 0,25€", default=0)
    qty_020 = fields.Integer(string="Cantidad 0,20€", default=0)
    qty_010 = fields.Integer(string="Cantidad 0,10€", default=0)
    qty_005 = fields.Integer(string="Cantidad 0,05€", default=0)
    qty_002 = fields.Integer(string="Cantidad 0,02€", default=0)

    # Totales calculados
    total = fields.Monetary(
        string="Total",
        compute="_compute_total",
        store=False,
        currency_field="currency_id",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    # ID del wizard de cierre para actualizar el valor
    closing_wizard_id = fields.Many2one(
        "pos.session.closing.wizard", string="Wizard de cierre"
    )

    # ID del wizard de entrada/salida de efectivo para actualizar el valor
    cash_move_wizard_id = fields.Many2one(
        "pos.session.cash_move.wizard", string="Wizard de entrada/salida de efectivo"
    )

    @api.depends(
        "qty_200",
        "qty_100",
        "qty_50",
        "qty_20",
        "qty_10",
        "qty_5",
        "qty_2",
        "qty_1",
        "qty_050",
        "qty_025",
        "qty_020",
        "qty_010",
        "qty_005",
        "qty_002",
    )
    def _compute_total(self):
        for wizard in self:
            total = (
                wizard.qty_200 * 200.0
                + wizard.qty_100 * 100.0
                + wizard.qty_50 * 50.0
                + wizard.qty_20 * 20.0
                + wizard.qty_10 * 10.0
                + wizard.qty_5 * 5.0
                + wizard.qty_2 * 2.0
                + wizard.qty_1 * 1.0
                + wizard.qty_050 * 0.50
                + wizard.qty_025 * 0.25
                + wizard.qty_020 * 0.20
                + wizard.qty_010 * 0.10
                + wizard.qty_005 * 0.05
                + wizard.qty_002 * 0.02
            )
            wizard.total = total

    def action_confirm(self):

        self.ensure_one()

        if self.closing_wizard_id:
            # Actualizar solo el campo cash_register_balance_end_real del wizard de cierre
            self.closing_wizard_id.write(
                {
                    "cash_register_balance_end_real": self.total,
                }
            )

            # Cerrar solo este wizard y volver al wizard de cierre
            return {
                "type": "ir.actions.act_window",
                "res_model": "pos.session.closing.wizard",
                "res_id": self.closing_wizard_id.id,
                "view_mode": "form",
                "target": "new",
                "context": self.env.context,
            }

        if self.cash_move_wizard_id:
            # Actualizar el campo amount del wizard de entrada/salida
            self.cash_move_wizard_id.write(
                {
                    "amount": self.total,
                }
            )

            # Cerrar solo este wizard y volver al wizard de entrada/salida
            return {
                "type": "ir.actions.act_window",
                "res_model": "pos.session.cash_move.wizard",
                "res_id": self.cash_move_wizard_id.id,
                "view_mode": "form",
                "target": "new",
                "context": self.env.context,
            }

        return {"type": "ir.actions.act_window_close"}

    def action_cancel(self):

        self.ensure_one()

        if self.closing_wizard_id:
            # Volver al wizard de cierre sin modificar el valor
            return {
                "type": "ir.actions.act_window",
                "res_model": "pos.session.closing.wizard",
                "res_id": self.closing_wizard_id.id,
                "view_mode": "form",
                "target": "new",
                "context": self.env.context,
            }

        if self.cash_move_wizard_id:
            # Volver al wizard de entrada/salida sin modificar el valor
            return {
                "type": "ir.actions.act_window",
                "res_model": "pos.session.cash_move.wizard",
                "res_id": self.cash_move_wizard_id.id,
                "view_mode": "form",
                "target": "new",
                "context": self.env.context,
            }

        return {"type": "ir.actions.act_window_close"}

    # Métodos de incremento
    def increment_200(self):
        self.qty_200 += 1
        return self._reload_view()

    def increment_100(self):
        self.qty_100 += 1
        return self._reload_view()

    def increment_50(self):
        self.qty_50 += 1
        return self._reload_view()

    def increment_20(self):
        self.qty_20 += 1
        return self._reload_view()

    def increment_10(self):
        self.qty_10 += 1
        return self._reload_view()

    def increment_5(self):
        self.qty_5 += 1
        return self._reload_view()

    def increment_2(self):
        self.qty_2 += 1
        return self._reload_view()

    def increment_1(self):
        self.qty_1 += 1
        return self._reload_view()

    def increment_050(self):
        self.qty_050 += 1
        return self._reload_view()

    def increment_025(self):
        self.qty_025 += 1
        return self._reload_view()

    def increment_020(self):
        self.qty_020 += 1
        return self._reload_view()

    def increment_010(self):
        self.qty_010 += 1
        return self._reload_view()

    def increment_005(self):
        self.qty_005 += 1
        return self._reload_view()

    def increment_002(self):
        self.qty_002 += 1
        return self._reload_view()

    # Métodos de decremento
    def decrement_200(self):
        if self.qty_200 > 0:
            self.qty_200 -= 1
        return self._reload_view()

    def decrement_100(self):
        if self.qty_100 > 0:
            self.qty_100 -= 1
        return self._reload_view()

    def decrement_50(self):
        if self.qty_50 > 0:
            self.qty_50 -= 1
        return self._reload_view()

    def decrement_20(self):
        if self.qty_20 > 0:
            self.qty_20 -= 1
        return self._reload_view()

    def decrement_10(self):
        if self.qty_10 > 0:
            self.qty_10 -= 1
        return self._reload_view()

    def decrement_5(self):
        if self.qty_5 > 0:
            self.qty_5 -= 1
        return self._reload_view()

    def decrement_2(self):
        if self.qty_2 > 0:
            self.qty_2 -= 1
        return self._reload_view()

    def decrement_1(self):
        if self.qty_1 > 0:
            self.qty_1 -= 1
        return self._reload_view()

    def decrement_050(self):
        if self.qty_050 > 0:
            self.qty_050 -= 1
        return self._reload_view()

    def decrement_025(self):
        if self.qty_025 > 0:
            self.qty_025 -= 1
        return self._reload_view()

    def decrement_020(self):
        if self.qty_020 > 0:
            self.qty_020 -= 1
        return self._reload_view()

    def decrement_010(self):
        if self.qty_010 > 0:
            self.qty_010 -= 1
        return self._reload_view()

    def decrement_005(self):
        if self.qty_005 > 0:
            self.qty_005 -= 1
        return self._reload_view()

    def decrement_002(self):
        if self.qty_002 > 0:
            self.qty_002 -= 1
        return self._reload_view()

    def _reload_view(self):
        """Método auxiliar para recargar la vista actual sin cerrarla"""
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }
