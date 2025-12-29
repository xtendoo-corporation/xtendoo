=================================================================
MIS Report Enhanced Viewer (xtendoo_mis_report_viewer)
=================================================================

This module provides a modern and interactive viewer for MIS Builder reports, imitating
the look and feel of Odoo Enhanced Accounting reports.

Features
========

- **Enhanced UX**: Clean table structure, hierarchical rows with caret expansion.
- **Interactive**: Update filters and parameters without reloading the page.
- **Linkable URL**: Report state (filters, etc.) is stored in the URL search parameters.
- **Exporting**: Direct access to PDF and XLSX exports.

Usage
=====

1. Install the module.
2. Go to **Accounting > Reports > MIS Viewer (Enhanced)**.
3. Select or pass a ``report_instance_id`` (e.g., in the URL or via the button in the MIS
   Report Instance form).
4. Use the "Enhanced Viewer" button directly from any MIS Report Instance form to open
   the modern viewer.

URL Structure
=============

You can open a report directly using a URL like:
``/odoo/action-xtendoo_mis_report_viewer?report_instance_id=1``

MigReport Integration
=====================

The module is prepared with hooks in ``controllers/main.py`` and
``models/mis_report_instance.py`` to connect with the MigReport engine if available. By
default, it uses standard MIS Builder PDF/XLSX exports.

Technical Details
=================

Options Structure
-----------------

The ``options`` object follows a structure similar to Odoo's ``account_reports``:

.. code-block:: json

    {
      "date": {"date_from": "2024-01-01", "date_to": "2024-12-31", "filter": "custom"},
      "comparison": {"filter": "previous_period", "number_of_periods": 1},
      "company_ids": [1],
      "unfolded_lines": ["line_1", "line_5"],
      "unfold_all": false
    }
