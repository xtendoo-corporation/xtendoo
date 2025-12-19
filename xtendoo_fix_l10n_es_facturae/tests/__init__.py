# -*- coding: utf-8 -*-
# Copyright 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

"""
Test para verificar que cleanup_xml_node se aplica correctamente

Para probar manualmente:
1. Instalar el módulo xtendoo_fix_l10n_es_facturae
2. Generar una factura Facturae
3. Verificar que el XML no contiene elementos vacíos
4. Comparar con una factura generada sin el módulo

El XML resultante debe estar libre de:
- Elementos vacíos como <InvoiceSeriesCode/>
- Espacios en blanco innecesarios
- Elementos con solo texto en blanco
"""

