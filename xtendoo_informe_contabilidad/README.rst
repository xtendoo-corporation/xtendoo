======================================
Informe Contabilidad - Diario Facturas
======================================
.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
|badge1| |badge2|
Este módulo genera un informe **Excel (XLSX)** con el **diario de facturas de
clientes** entre dos fechas.
El informe incluye las siguientes columnas:
* **Serie**: Código del diario contable
* **Número de factura**: Número de la factura
* **Fecha**: Fecha de emisión de la factura
* **Referencia del cliente**: Referencia indicada en la factura
* **Neto**: Importe base imponible (sin IVA)
* **Importe IVA**: Importe total del IVA
* **Total factura**: Importe total (Neto + IVA)
El informe también incluye una **hoja de resumen** con los totales agrupados
por serie/diario.
Uso
---
#. Ir a **Contabilidad → Informes → Informe Diario de Facturas**
#. Indicar el rango de fechas (obligatorio)
#. Opcionalmente filtrar por diario de ventas o cliente
#. Pulsar **Generar Informe Excel**
#. El archivo se descargará automáticamente
Requisitos
----------
* Python: ``xlsxwriter``
Instalación de dependencias::
    pip install xlsxwriter
Autor
-----
* `Xtendoo <https://xtendoo.es>`_
Licencia
--------
Este módulo se distribuye bajo la licencia `AGPL-3 <https://www.gnu.org/licenses/agpl-3.0.html>`_.
