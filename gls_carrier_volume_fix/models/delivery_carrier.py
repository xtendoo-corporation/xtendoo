from xml.sax.saxutils import escape

from odoo import models, fields, _
from odoo.exceptions import UserError

class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    def _prepare_gls_asm_shipping(self, picking):
        """Convert picking values for asm api
        :param picking record with picking to send
        :returns dict values for the connector
        """
        self.ensure_one()
        # A picking can be delivered from any warehouse
        sender_partner = (
            picking.picking_type_id.warehouse_id.partner_id
            or picking.company_id.partner_id
        )
        consignee = picking.partner_id
        consignee_entity = picking.partner_id.commercial_partner_id
        if not sender_partner.street:
            raise UserError(_("Couldn't find the sender street"))
        cash_amount = 0
        if self.gls_asm_cash_on_delivery:
            cash_amount = picking.sale_id.amount_total
        return {
            "fecha": fields.Date.today().strftime("%d/%m/%Y"),
            "portes": self.gls_asm_postage_type,
            "servicio": self.gls_asm_service,
            "horario": self.gls_asm_shiptime,
            "bultos": picking.number_of_packages,
            "peso": round(picking.shipping_weight, 3),
            "volumen": round(picking.volume, 3),
            "declarado": "",  # [optional]
            "dninomb": "0",  # [optional]
            "fechaentrega": "",  # [optional]
            "retorno": "1" if self.gls_asm_with_return else "0",  # [optional]
            "pod": "N",  # [optional]
            "podobligatorio": "N",  # [deprecated]
            "remite_plaza": "",  # [optional] Origin agency
            "remite_nombre": escape(
                sender_partner.name or sender_partner.parent_id.name
            ),
            "remite_direccion": escape(sender_partner.street or ""),
            "remite_poblacion": escape(sender_partner.city or ""),
            "remite_provincia": escape(sender_partner.state_id.name or ""),
            "remite_pais": "34",  # [mandatory] always 34=Spain
            "remite_cp": sender_partner.zip or "",
            "remite_telefono": sender_partner.phone or "",
            "remite_movil": sender_partner.mobile or "",
            "remite_email": escape(sender_partner.email or ""),
            "remite_departamento": "",
            "remite_nif": sender_partner.vat or "",
            "remite_observaciones": "",
            "destinatario_codigo": "",
            "destinatario_plaza": "",
            "destinatario_nombre": (
                escape(consignee.name or consignee.commercial_partner_id.name or "")
            ),
            "destinatario_direccion": escape(consignee.street or ""),
            "destinatario_poblacion": escape(consignee.city or ""),
            "destinatario_provincia": escape(consignee.state_id.name or ""),
            "destinatario_pais": consignee.country_id.phone_code or "",
            "destinatario_cp": consignee.zip,
            # For certain destinations the consignee mobile and email are required to
            # make the expedition. Try to fallback to the commercial entity one
            "destinatario_telefono": consignee.phone or consignee_entity.phone or "",
            "destinatario_movil": consignee.mobile or consignee_entity.mobile or "",
            "destinatario_email": escape(
                consignee.email or consignee_entity.email or ""
            ),
            "destinatario_observaciones": picking.gls_shipping_notes or "",
            "destinatario_att": "",
            "destinatario_departamento": "",
            "destinatario_nif": "",
            "referencia_c": escape(
                picking.name.replace("\\", "/")  # It errors with \ characters
            ),  # Our unique reference
            "referencia_0": "",  # Not used if the above is set
            "importes_debido": "0",  # The customer pays the shipping
            "importes_reembolso": cash_amount or "",
            "seguro": "0",  # [optional]
            "seguro_descripcion": "",  # [optional]
            "seguro_importe": "",  # [optional]
            "etiqueta": "PDF",  # Get Label in response
            "etiqueta_devolucion": "PDF",
            # [optional] GLS Customer Code
            # (when customer have several codes in GLS)
            "cliente_codigo": "",
            "cliente_plaza": "",
            "cliente_agente": "",
        }
