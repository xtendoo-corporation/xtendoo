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

    def _get_captured_payments_domain(self):
        """
        Override para excluir pagos de pedidos vinculados a sale.order del cálculo del balance.
        Estos pedidos se gestionan en cuenta cliente y no afectan al arqueo de caja.
        """
        # Obtener IDs de pedidos vinculados a sale.order
        linked_order_ids = self.order_ids.filtered(lambda o: o.linked_sale_order_id).ids

        # Dominio base de Odoo
        domain = [
            ("session_id", "in", self.ids),
            ("pos_order_id.state", "in", ["paid", "done"]),
        ]

        # Excluir pagos de pedidos vinculados
        if linked_order_ids:
            domain.append(("pos_order_id", "not in", linked_order_ids))

        return domain

    def _get_closed_orders(self):
        """
        Override para excluir pedidos vinculados a sale.order del proceso de cierre.
        Al excluirlos aquí, no se tienen en cuenta para la validación de importes
        ni para la creación de asientos contables de sesión.
        """
        return self.order_ids.filtered(
            lambda o: o.state not in ["draft", "cancel"] and not o.linked_sale_order_id
        )

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
        de sesiones en modo no táctil.
        """
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
