# -*- coding: utf-8 -*-
{
    'name': 'Xtendoo DeCA - Documento Electrónico de Control Administrativo',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Delivery',
    'author': 'Xtendoo',
    'website': 'https://xtendoo.es',
    'license': 'AGPL-3',
    'summary': (
        'Generación del DeCA (Resolución DGTCF de 5/6/2026, BOE-A-2026-12784) '
        'para transporte público de mercancías por carretera'
    ),
    'description': """
Xtendoo DeCA
============
Genera el Documento Electrónico de Control Administrativo (DeCA), obligatorio
desde el 5 de octubre de 2026 para el transporte público de mercancías por
carretera en España:

- Disposición transitoria octava, Ley 9/2025, de 3 de diciembre, de Movilidad
  Sostenible.
- Resolución de 5 de junio de 2026, de la Dirección General de Transporte por
  Carretera y Ferrocarril (BOE-A-2026-12784), que sustituye a la de 22 de mayo
  de 2023.
- Datos exigidos: artículo 6 de la Orden FOM/2861/2012, de 13 de diciembre.

Funcionalidad de esta primera versión (sobre albaranes de salida / stock.picking):

- Captura en el albarán de los datos del cargador contractual, transportista
  efectivo, origen/destino, naturaleza y peso de la mercancía, matrícula del
  vehículo, autorización especial y fecha de realización del transporte.
- Generación de un PDF nativo digital (no escaneado) con un código QR que
  enlaza a una URL pública, única, en HTTPS, de descarga directa sin
  autenticación ni interacción manual (apartados Segundo y Tercero de la
  Resolución).
- Registro de fecha/hora de creación y modificación como metadatos del
  documento y conservación del fichero como adjunto de Odoo.
- Trazabilidad de modificaciones: al regenerar el DeCA se conserva el
  documento anterior y su PDF (apartado Quinto de la Resolución).
- Desactivación automática de la descarga a los 7 días naturales de la fecha
  de servicio (apartado Tercero.5, opcional según la norma).

Fuera de alcance de esta primera versión (ver hoja de ruta en el proyecto):

- Firma electrónica avanzada/cualificada eIDAS (solo exigida si el DeCA
  también se usa con fines contractuales).
- Agrupación de varios envíos en un mismo DeCA (apartado Sexto).
- Integración con el Reglamento eFTI (UE) 2020/1056 o con la plataforma
  pública SIMPLE como vía alternativa de cumplimiento.
- Hoja electrónica de Ruta (HeRU) para transporte de viajeros.
- Integración con el documento de transporte ADR (mercancías peligrosas).
""",
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'report/deca_report_templates.xml',
        'report/deca_report_actions.xml',
        'views/xtendoo_deca_document_views.xml',
        'views/stock_picking_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
