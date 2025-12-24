# -*- coding: utf-8 -*-
# Copyright 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from lxml import etree

from odoo import api, models
from odoo.tools import cleanup_xml_node


class ReportXmlAbstract(models.AbstractModel):
    """
    Extend report.report_xml.abstract to apply cleanup_xml_node
    to all XML reports, removing empty elements and whitespace.
    """

    _inherit = "report.report_xml.abstract"

    @api.model
    def generate_report(self, ir_report, docids, data=None):
        """
        Override generate_report to apply cleanup_xml_node to the result.

        This ensures that all XML reports generated will have:
        - Empty elements removed
        - Whitespace cleaned up
        - Proper XML formatting
        - XML declaration with double quotes

        Similar to the approach used in l10n_es_facturae module.
        """
        # Call parent method to generate the XML
        xml_content, content_type = super().generate_report(ir_report, docids, data=data)

        # Apply cleanup_xml_node to remove empty elements and whitespace
        tree = cleanup_xml_node(xml_content)

        # Convert back to string with proper encoding
        encoding = ir_report.xml_encoding or "UTF-8"
        xml_content = etree.tostring(
            tree,
            xml_declaration=False,  # Generate declaration manually to use double quotes
            encoding=encoding,
            pretty_print=True,
        )

        # Add XML declaration with double quotes if needed
        if ir_report.xml_declaration:
            declaration = f'<?xml version="1.0" encoding="{encoding}"?>\n'.encode(encoding)
            xml_content = declaration + xml_content

        print("xml_content:", xml_content)
        print("XML Report Generated:\n", xml_content.decode(encoding))
        print("content_type:", content_type)

        return xml_content, content_type

