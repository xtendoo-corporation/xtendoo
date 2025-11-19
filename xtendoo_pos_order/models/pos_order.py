# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Valida que la creación manual de órdenes POS solo sea posible
        cuando la caja está configurada en modo 'backend'.

        Esto previene la creación accidental de órdenes inconsistentes
        desde el backend cuando el POS debe usarse normalmente desde el frontend.
        """
        for vals in vals_list:
            # Obtener el config_id de los valores o del contexto
            config_id = vals.get("config_id") or self.env.context.get("default_config_id")

            if not config_id:
                raise UserError(
                    _("Debe especificar un Punto de Venta (config_id) para crear una orden.")
                )

            # Verificar si estamos creando desde el frontend del POS
            # (el frontend JS suele pasar un flag especial en el contexto)
            from_ui = self.env.context.get("from_pos_ui", False)

            # Si la orden viene del frontend JS, permitir siempre
            if from_ui:
                continue

            # Si es creación manual desde backend, validar el interface_type
            pos_config = self.env["pos.config"].browse(config_id)

            if pos_config.interface_type != "backend":
                raise UserError(
                    _(
                        "No se permite crear órdenes manualmente para el Punto de Venta '%s'.\n\n"
                        "Este POS está configurado para usar la interfaz estándar (Frontend).\n"
                        "Para crear órdenes manualmente desde el backend, debe cambiar "
                        "la configuración del POS a 'Backend Orders Interface' en:\n"
                        "Punto de Venta → Configuración → %s → Interface Type"
                    ) % (pos_config.name, pos_config.name)
                )

            # Validar que exista una sesión abierta
            session_id = vals.get("session_id") or self.env.context.get("default_session_id")

            if not session_id:
                # Buscar sesión abierta para este POS
                open_session = self.env["pos.session"].search(
                    [("config_id", "=", config_id), ("state", "=", "opened")],
                    limit=1,
                )

                if not open_session:
                    raise UserError(
                        _(
                            "No hay ninguna sesión abierta para el Punto de Venta '%s'.\n\n"
                            "Debe abrir una sesión antes de crear órdenes.\n"
                            "Vaya a: Punto de Venta → Configuración → %s → Abrir Sesión"
                        ) % (pos_config.name, pos_config.name)
                    )

                vals["session_id"] = open_session.id

            # Asegurar que se asigne partner_id si no existe
            if not vals.get("partner_id"):
                # Buscar el cliente genérico o crear uno por defecto
                default_partner = pos_config.default_partner_id
                if default_partner:
                    vals["partner_id"] = default_partner.id

        return super().create(vals_list)

    @api.depends("lines.price_subtotal_incl", "lines.price_subtotal")
    def _compute_amount_all(self):
        """
        Asegura que los totales se calculen correctamente desde el backend.
        Reutiliza la lógica estándar de Odoo.
        """
        return super()._compute_amount_all()

    def action_pos_order_paid(self):
        """
        Marca la orden como pagada.
        Usado desde el backend cuando se completan los pagos.
        """
        self.ensure_one()

        # Validar que la suma de pagos cubra el total
        total_payments = sum(self.payment_ids.mapped("amount"))

        if total_payments < self.amount_total:
            raise UserError(
                _(
                    "El total de pagos (%.2f) no cubre el total de la orden (%.2f).\n"
                    "Agregue más líneas de pago para completar la orden."
                ) % (total_payments, self.amount_total)
            )

        return super().action_pos_order_paid()

    def action_pos_order_invoice(self):
        """
        Permite generar factura desde una orden del backend.
        Reutiliza la lógica estándar del POS.
        """
        self.ensure_one()

        if not self.partner_id:
            raise UserError(
                _("Debe especificar un cliente para generar la factura.")
            )

        return super().action_pos_order_invoice()

