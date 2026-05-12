# © 2024 Xtendoo. See LICENSE file for full copyright and licensing details.
import logging

from urllib.parse import urlencode

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
# format_list no está disponible en esta versión de Odoo 17

from .envia_request import Envia

_logger = logging.getLogger(__name__)

ENVIA_STOCK_TYPE = [
    ('PAPER_4X6', 'PAPER_4X6'),
    ('PAPER_4X8', 'PAPER_4X8'),
    ('PAPER_7X4.75', 'PAPER_7X4.75'),
    ('PAPER_8.27X11.67', 'PAPER_8.27X11.67'),
    ('PAPER_8.5X11_BOTTOM_HALF_LABEL', 'PAPER_8.5X11_BOTTOM_HALF_LABEL'),
    ('PAPER_8.5X11', 'PAPER_8.5X11'),
    ('STOCK_2.4X6', 'STOCK_2.4X6'),
    ('STOCK_2.9X5', 'STOCK_2.9X5'),
    ('STOCK_3.8X4.2', 'STOCK_3.8X4.2'),
    ('STOCK_3.9X7', 'STOCK_3.9X7'),
    ('STOCK_4X4', 'STOCK_4X4'),
    ('STOCK_4X6', 'STOCK_4X6'),
    ('STOCK_4X6.5', 'STOCK_4X6.5'),
    ('STOCK_4X6.75_LEADING_DOC_TAB', 'STOCK_4X6.75_LEADING_DOC_TAB'),
    ('STOCK_4X7.5', 'STOCK_4X7.5'),
    ('STOCK_4X8', 'STOCK_4X8'),
]


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('envia', 'Envia')],
        ondelete={'envia': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})},
    )

    envia_production_api_key = fields.Text(
        string="Envia Production Access Token",
        help="Genera un Access Token desde el Portal de Producción de Envia",
        copy=False,
        groups="base.group_system",
    )

    envia_sandbox_api_key = fields.Text(
        string="Envia Sandbox Access Token",
        help="Genera un Access Token desde el Portal Sandbox de Envia",
        copy=False,
        groups="base.group_system",
    )

    envia_default_package_type_id = fields.Many2one(
        "stock.package.type",
        string="Envia Default Package",
        domain="[('package_carrier_type', '=', 'envia')]",
        help="Envia requiere dimensiones del paquete para obtener tarifas precisas. "
             "Puedes definirlas en un tipo de paquete que establezcas como predeterminado.",
    )

    envia_mail_type = fields.Selection(
        related='envia_default_package_type_id.envia_mail_type',
    )

    envia_carrier_code = fields.Char(
        string='Envia.com Carrier Code',
        store=True,
        help='El transportista en Envia.com usado por este carrier. El código de servicio le pertenece.',
        compute='_compute_services',
    )

    envia_service_code = fields.Char(
        string='Envia.com Service Code',
        store=True,
        help='El servicio que se usará para este carrier. Se establece al seleccionar un carrier desde el asistente.',
        compute='_compute_services',
    )

    envia_service_name = fields.Char(
        string='Envia.com Service Name',
        store=True,
        help='El servicio que se usará para este carrier. Se establece al seleccionar un carrier desde el asistente.',
        compute='_compute_services',
    )

    envia_currency_id = fields.Many2one(
        'res.currency',
        string="Envia Account Main Currency",
        copy=False,
        default=lambda self: self.env.company.currency_id,
        help="Moneda configurada en Envia",
    )

    envia_label_stock_type = fields.Selection(
        selection=ENVIA_STOCK_TYPE,
        string='Envia Label Type',
        help='Selecciona el tamaño de la etiqueta',
        default='PAPER_8.5X11',
    )

    envia_label_file_type = fields.Selection(
        selection=[
            ('PNG', 'PNG'),
            ('ZPLII', 'ZPLII'),
            ('EPL', 'EPL'),
            ('PDF', 'PDF'),
            ('ZPL', 'ZPL'),
        ],
        string='Envia Label File Type',
        help='Selecciona el formato de impresión de la etiqueta',
        default='PDF',
    )

    country_id = fields.Many2one(
        'res.country',
        string='Ship From',
        default=lambda self: self.env.company.country_id,
        help="Selecciona el país que usará este método de envío",
    )

    envia_return_at_senders_expense = fields.Boolean(
        string='Returned at Shippers Expense',
        default=False,
        help='Si el transportista no puede entregar el paquete, este puede devolverse al remitente '
             'o abandonarse en la puerta. (Solo Canadá)',
    )

    envia_lift_pickup = fields.Boolean(
        string='Lift Assistance on Pickup',
        default=False,
        help='Proporcionar asistencia de montacargas si el proveedor no tiene muelle o montacargas para cargar el envío. '
             '(Solo Estados Unidos y México)',
    )

    envia_lift_delivery = fields.Boolean(
        string='Lift Assistance on Delivery',
        default=False,
        help='Proporcionar asistencia de montacargas si el destinatario no tiene muelle o montacargas para descargar el envío. '
             '(Solo Estados Unidos y México)',
    )

    envia_residential_delivery = fields.Boolean(
        string='Delivery Residential Zone',
        default=False,
        help='Ciertos transportistas como UPS cobran un cargo adicional por entregas en zona residencial. '
             '(Solo Estados Unidos)',
    )

    envia_residential_pickup = fields.Boolean(
        string='Pickup Residential Zone',
        default=False,
        help='Ciertos transportistas como UPS cobran un cargo adicional por recogidas en zonas residenciales. '
             '(Solo Estados Unidos)',
    )

    @api.depends('country_id', 'envia_default_package_type_id.envia_mail_type', 'prod_environment')
    def _compute_services(self):
        """Cada país tiene diferentes carriers o servicios.
        Además, dependiendo del tipo de correo, habrá diferentes servicios disponibles.
        El entorno de producción también tiene servicios distintos.
        """
        for carrier in self:
            if carrier.delivery_type == 'envia':
                carrier.envia_carrier_code = ""
                carrier.envia_service_code = ""
                carrier.envia_service_name = ""

    def _compute_supports_shipping_insurance(self):
        # Compatibilidad: el método padre puede no existir en Odoo 17
        try:
            super()._compute_supports_shipping_insurance()
        except AttributeError:
            pass
        for carrier in self:
            if carrier.delivery_type == 'envia':
                carrier.supports_shipping_insurance = True

    def _get_delivery_label_prefix(self):
        """Prefijo de la etiqueta de envío. Fallback para Odoo 17."""
        try:
            return super()._get_delivery_label_prefix()
        except AttributeError:
            return 'LabelShipping'

    def _get_delivery_doc_prefix(self):
        """Prefijo del documento de envío. Fallback para Odoo 17."""
        try:
            return super()._get_delivery_doc_prefix()
        except AttributeError:
            return 'Document'

    def _envia_convert_weight(self, weight):
        """Devuelve el peso en KG para un pedido Envia."""
        self.ensure_one()
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        return weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_kgm'), round=False)

    def _envia_convert_size(self, size):
        """Devuelve el tamaño en CM para un pedido Envia."""
        self.ensure_one()
        size_uom_id = self.env['product.template']._get_length_uom_id_from_ir_config_parameter()
        return size_uom_id._compute_quantity(size, self.env.ref('uom.product_uom_cm'), round=False)

    def action_open_envia_wizard(self):
        """Obtiene carriers y canales desde la cuenta Envia.
        Crea registros de carriers en Odoo.
        """
        self.ensure_one()
        if self.delivery_type != 'envia':
            raise ValidationError(_('Esta acción requiere un carrier de Envia.com.'))

        envia = Envia(self, self.prod_environment, self.log_xml)
        carriers_data = envia._fetch_envia_carriers()

        if errors_found := carriers_data.get('error'):
            raise ValidationError(errors_found)
        carriers_list = carriers_data.get('carriers')
        if not carriers_list:
            raise ValidationError(_("No se pudieron obtener los Carriers de Envia. Por favor inténtalo de nuevo más tarde."))

        return {
            'name': _("Elige un Servicio de Envío de Envia.com"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'envia.shipping.wizard',
            'target': 'new',
            'context': {
                'default_carrier_id': self.id,
                'default_available_services': carriers_list,
                'default_selected_service_code': self.envia_service_code,
                'default_selected_carrier_code': self.envia_carrier_code,
            },
        }

    def envia_rate_shipment(self, order):
        """Devuelve la tarifa de envío para el pedido y el método de envío seleccionado."""
        if not self.envia_carrier_code or not self.envia_service_code:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _(
                    "No hay carrier configurado en \"%(delivery_method)s\". Para usar Envia.com, necesitas sincronizar tus carriers con tu cuenta.",
                    delivery_method=self.name
                ),
                'warning_message': False,
            }

        order_weight = self.env.context.get('order_weight', None)
        envia = Envia(self, self.prod_environment, self.log_xml)
        result = envia._rate_request(
            order.partner_shipping_id,
            order.warehouse_id.partner_id or order.warehouse_id.company_id.partner_id,
            order,
            order_weight=order_weight,
        )

        if result.get('error_found'):
            return {
                'success': False,
                'price': 0.0,
                'error_message': result['error_found'],
                'warning_message': False,
            }

        price = float(result['price'])
        return {
            'success': True,
            'price': price,
            'error_message': False,
            'warning_message': result.get('warning_message'),
        }

    def envia_send_shipping(self, pickings):
        """Envía el shipment a Envia para validación.
        Agrega el envío al carrito, hace checkout y genera la etiqueta.
        """
        if not self.envia_carrier_code or not self.envia_service_code:
            raise UserError(_(
                "No hay carrier configurado en \"%(delivery_method)s\". Para usar Envia.com, necesitas sincronizar tus carriers con tu cuenta.",
                delivery_method=self.name
            ))
        res = []
        envia = Envia(self, self.prod_environment, self.log_xml)
        for pick in pickings:
            shipment = envia._send_shipping(pick)
            res.append({
                'tracking_number': shipment.get('tracking_number'),
                'exact_price': shipment.get('exact_price'),
            })
        return res

    def envia_get_tracking_link(self, picking):
        """Devuelve el enlace de seguimiento para un picking."""
        if self.prod_environment:
            root_url = "https://envia.com"
        else:
            root_url = "https://dev.envia.com"

        params = {'label': picking.carrier_tracking_ref}
        return f"{root_url}/tracking?{urlencode(params)}"

    def envia_cancel_shipment(self, pickings):
        """Intenta cancelar el envío en el backend de Envia.
        Puede fallar si el envío ya fue despachado o la etiqueta fue retirada por el transportista.
        """
        envia = Envia(self, self.prod_environment, self.log_xml)
        for pick in pickings:
            if pick.carrier_id.delivery_type != 'envia' or not pick.carrier_tracking_ref:
                pick.message_post(body=_("¡No se encontraron órdenes de Envia para cancelar el envío!"))
                continue

            invalid_trackings = envia._cancel_picking(pick)
            if invalid_trackings:
                order_numbers = ", ".join(str(t) for t in invalid_trackings)
                pick.message_post(body=_("No se pudo cancelar la orden: %(order_number)s", order_number=order_numbers))
            else:
                pick.write({
                    "carrier_tracking_ref": '',
                    "carrier_price": 0.00,
                })

