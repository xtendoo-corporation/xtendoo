from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = "pos.session"

    # Campo para mostrar el total de ventas a cuenta cliente (pedidos vinculados a sale.order)
    linked_sale_orders_total = fields.Monetary(
        string="Total Cuenta Cliente",
        compute="_compute_linked_sale_orders_total",
        store=False,
        help="Total de pedidos POS vinculados a pedidos de venta tradicionales (cuenta cliente)",
    )

    linked_sale_orders_count = fields.Integer(
        string="Pedidos a Cuenta",
        compute="_compute_linked_sale_orders_total",
        store=False,
        help="Número de pedidos POS vinculados a pedidos de venta tradicionales",
    )

    @api.depends(
        "order_ids", "order_ids.linked_sale_order_id", "order_ids.amount_total"
    )
    def _compute_linked_sale_orders_total(self):
        """Calcula el total y cantidad de pedidos vinculados a sale.order (cuenta cliente)"""
        for session in self:
            linked_orders = session.order_ids.filtered(lambda o: o.linked_sale_order_id)
            session.linked_sale_orders_count = len(linked_orders)
            session.linked_sale_orders_total = sum(
                order.amount_total for order in linked_orders
            )

    # _validate_session override removed as it was only for excluding linked orders

    def action_pos_session_closing_control(
        self,
        balancing_account=False,
        amount_to_balance=0,
        bank_payment_method_diffs=None,
    ):
        """
        Override para permitir el cierre de sesión aunque haya pedidos en draft
        que estén vinculados a sale.order.
        """
        bank_payment_method_diffs = bank_payment_method_diffs or {}

        for session in self:
            # Obtener pedidos en borrador
            draft_orders = [
                order for order in session.order_ids if order.state == "draft"
            ]

            if draft_orders:
                raise UserError(
                    _(
                        "No puede cerrar el TPV si aún hay pedidos en borrador para este día."
                    )
                )

            if session.state == "closed":
                raise UserError(_("Esta sesión ya está cerrada."))

            stop_at = session.stop_at or fields.Datetime.now()
            session.write({"state": "closing_control", "stop_at": stop_at})

            if not session.config_id.cash_control:
                return session.action_pos_session_close(
                    balancing_account, amount_to_balance, bank_payment_method_diffs
                )

            if session.rescue and session.config_id.cash_control:
                default_cash_payment_method_id = session.payment_method_ids.filtered(
                    lambda pm: pm.type == "cash"
                )
                if default_cash_payment_method_id:
                    default_cash_payment_method_id = default_cash_payment_method_id[0]
                    orders = session._get_closed_orders()
                    total_cash = (
                        sum(
                            orders.payment_ids.filtered(
                                lambda p: p.payment_method_id
                                == default_cash_payment_method_id
                            ).mapped("amount")
                        )
                        + session.cash_register_balance_start
                    )
                    session.cash_register_balance_end_real = total_cash

            return session.action_pos_session_validate(
                balancing_account, amount_to_balance, bank_payment_method_diffs
            )

    def _check_if_no_draft_orders(self):
        """
        Override para asegurar que no haya ningún pedido en borrador.
        """
        draft_orders = self.get_session_orders().filtered(
            lambda order: order.state == "draft"
        )
        if draft_orders:
            raise UserError(
                _(
                    "Aún hay pedidos en estado borrador en la sesión. "
                    "Pague o cancele los siguientes pedidos para validar la sesión:\n%s",
                    ", ".join(draft_orders.mapped("name")),
                )
            )
        return True

    def _cannot_close_session(self, bank_payment_method_diffs=None):
        """
        Override para excluir pedidos vinculados a sale.order de la validación de cierre.
        """
        bank_payment_method_diffs = bank_payment_method_diffs or {}

        # Considerar todos los pedidos en borrador
        draft_orders = [
            order for order in self.get_session_orders() if order.state == "draft"
        ]

        if draft_orders:
            return {
                "successful": False,
                "message": _(
                    "No puede cerrar el TPV si aún hay pedidos en borrador para este día."
                ),
                "redirect": False,
            }

        if self.state == "closed":
            return {
                "successful": False,
                "type": "alert",
                "title": "Session already closed",
                "message": _("La sesión ya ha sido cerrada por otro usuario."),
                "redirect": True,
            }

        if bank_payment_method_diffs:
            no_loss_account = self.env["account.journal"]
            no_profit_account = self.env["account.journal"]
            for payment_method in self.env["pos.payment.method"].browse(
                bank_payment_method_diffs.keys()
            ):
                journal = payment_method.journal_id
                if not journal.loss_account_id:
                    no_loss_account |= journal
                if not journal.profit_account_id:
                    no_profit_account |= journal
            message = ""
            if no_loss_account:
                message += _(
                    "Please set a Loss Account on the following journals: %s.\n",
                    ", ".join(no_loss_account.mapped("name")),
                )
            if no_profit_account:
                message += _(
                    "Please set a Profit Account on the following journals: %s.",
                    ", ".join(no_profit_account.mapped("name")),
                )
            if message:
                return {"successful": False, "message": message, "redirect": True}

        return False

    def get_closing_control_data(self):
        """
        Override para incluir información de pedidos a cuenta cliente en los datos de cierre.
        """
        result = super().get_closing_control_data()

        # Añadir información de pedidos vinculados a sale.order
        for session in self:
            linked_orders = session.order_ids.filtered(lambda o: o.linked_sale_order_id)
            if linked_orders:
                # Añadir sección de "Cuenta Cliente" a los datos de cierre
                result["linked_sale_orders"] = {
                    "count": len(linked_orders),
                    "total": sum(order.amount_total for order in linked_orders),
                    "orders": [
                        {
                            "id": order.id,
                            "name": order.name,
                            "partner": (
                                order.partner_id.name if order.partner_id else ""
                            ),
                            "amount_total": order.amount_total,
                            "sale_order_name": order.linked_sale_order_id.name,
                            "sale_order_id": order.linked_sale_order_id.id,
                        }
                        for order in linked_orders
                    ],
                }

        return result

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override del create para interceptar la apertura automática
        de sesiones en modo no táctil y asignar una secuencia automática.
        """
        # Asignar secuencia automática a cada sesión
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "/":
                sequence = self.env["ir.sequence"].next_by_code("pos.session")
                if sequence:
                    vals["name"] = sequence

        # Si estamos en contexto skip_auto_open, solo crear sin abrir wizard
        if self.env.context.get("skip_auto_open"):
            return super(PosSession, self).create(vals_list)

        # Si no hay skip_auto_open, usar el comportamiento estándar
        # (el wizard se abrirá desde open_ui si es necesario)
        return super(PosSession, self).create(vals_list)

    def action_pos_session_open(self):
        """
        Override del método estándar de apertura de sesión.
        """
        if self.env.context.get("skip_auto_open"):
            return True

        non_touch_sessions = self.filtered(
            lambda s: s.config_id.pos_non_touch and s.state == "opening_control"
        )
        normal_sessions = self - non_touch_sessions

        if normal_sessions:
            super(PosSession, normal_sessions).action_pos_session_open()

        if non_touch_sessions and not self.env.context.get("skip_auto_open"):
            return non_touch_sessions._open_non_touch_wizard()

        return True

    def _open_non_touch_wizard(self):
        """
        Abre el wizard de apertura de sesión para modo no táctil.
        """
        self.ensure_one()
        wizard = self.env["pos.session.opening.wizard"].create(
            {
                "session_id": self.id,
                "user_id": self.env.user.id,
            }
        )
        return {
            "name": _("Abrir sesión POS - Modo no táctil"),
            "type": "ir.actions.act_window",
            "res_model": "pos.session.opening.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }
