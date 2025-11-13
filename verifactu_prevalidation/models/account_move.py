# -*- coding: utf-8 -*-
# Extensión de `account.move` para prevalidar país del cliente antes de validar (post)
# Autor: dani
# Empresa: xtendoo

from odoo import models, _, api
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _check_partner_country_for_moves(self, moves):
        """Comprueba que las facturas (move) tienen partner con country.

        :param moves: recordset de account.move
        :return: None, lanza UserError si encuentra un partner sin country
        """
        partners_without_country = moves.mapped("partner_id").filtered(
            lambda p: not p.country_id
        )
        if partners_without_country:
            names = ", ".join(partners_without_country.mapped("name")[:5])
            plural = "s" if len(partners_without_country) > 1 else ""
            raise UserError(
                _(
                    "El cliente%s %s no tiene país configurado. Configure el país en la ficha del cliente antes de validar la factura."
                    % (plural, names)
                )
            )

    def action_post(self):
        """Override de `action_post` para validar previamente que el partner tenga país."""
        # Solo aplicar a facturas/abonos (out_invoice, in_invoice, out_refund, in_refund)
        moves_to_check = self.filtered(lambda m: m.move_type in ("out_invoice", "in_invoice", "out_refund", "in_refund"))
        if moves_to_check:
            # Evitar comprobar partners de facturas ya publicadas
            moves_to_check = moves_to_check.filtered(lambda m: not m.posted_before)
            if moves_to_check:
                self._check_partner_country_for_moves(moves_to_check)
        return super().action_post()

