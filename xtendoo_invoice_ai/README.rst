==========================
Invoice AI - OpenAI Integration
==========================

.. contents:: Table of Contents

Overview
========

This module allows you to automatically import vendor invoices using OpenAI (ChatGPT) vision and structured extraction capabilities.

Simply upload a PDF or image of a vendor invoice, and the system will:

* Extract supplier information (name, VAT, address, etc.)
* Extract invoice details (number, date, due date, currency)
* Extract all invoice lines with descriptions, quantities, prices, and taxes
* Create or find the supplier in Odoo
* Create a draft vendor bill ready for validation

Features
========

* **Direct OpenAI API integration**: No intermediate services required
* **Multi-page PDF support**: Process invoices with multiple pages
* **Image support**: JPG, PNG formats supported
* **Multi-company**: Works with multiple companies
* **Multi-currency**: Detects and handles different currencies
* **Automatic supplier creation**: Optionally create suppliers if not found
* **Tax mapping**: Intelligently maps extracted taxes to Odoo taxes
* **Product matching**: Matches products by code when available
* **Total validation**: Validates extracted totals against calculated amounts
* **Job history**: Track all imports with metrics (tokens, processing time)
* **GDPR compliant**: Configurable logging, optional file attachment

Installation
============

1. Install required Python dependencies:

.. code-block:: bash

    pip install openai pdf2image jsonschema

2. For PDF processing, you also need poppler-utils:

.. code-block:: bash

    # Ubuntu/Debian
    sudo apt-get install poppler-utils

    # macOS
    brew install poppler

    # Windows
    # Download from: https://github.com/oschwartz10612/poppler-windows/releases/

3. Install the module in Odoo from Apps menu

Configuration
=============

1. Go to **Settings → General → Integrations → OpenAI (ChatGPT)**

2. Configure the following parameters:

   * **OpenAI API Key**: Your API key from https://platform.openai.com/api-keys (required)
   * **OpenAI Model**: Model to use (default: gpt-4o, must support vision)
   * **OpenAI Base URL**: Optional custom endpoint for enterprise accounts
   * **Max Pages to Process**: Maximum PDF pages to process (default: 10)
   * **Temperature**: 0.0 for deterministic, 1.0 for creative (default: 0.0)
   * **Total Tolerance**: Maximum difference allowed between AI and calculated totals (default: 0.02)

3. Alternatively, you can set the API key via environment variable:

.. code-block:: bash

    export OPENAI_API_KEY="sk-proj-..."

Usage
=====

Import a Vendor Invoice
-----------------------

1. Go to **Accounting → Vendors → Import Invoice with AI**

2. Fill in the wizard:

   * **Invoice File**: Upload PDF, JPG, or PNG of the vendor invoice
   * **Company**: Select company (multi-company environments)
   * **Purchase Journal**: Optionally select a specific purchase journal
   * **Force Currency**: Optionally override detected currency
   * **Create Partner if Missing**: Enable to automatically create suppliers
   * **Attach Original File**: Enable to attach the uploaded file to the invoice

3. Click **Analyze and Create Invoice**

4. The system will:

   * Send the file to OpenAI for analysis
   * Extract all invoice data
   * Create or find the supplier
   * Create a draft vendor bill
   * Open the bill for your review

5. Review the created bill and validate it when ready

View Import History
-------------------

Go to **Accounting → Vendors → AI Import History** to see:

* All import jobs (success and errors)
* Processing time and token usage
* Extracted data summary
* Link to created invoices

Technical Details
=================

Data Extraction Schema
----------------------

The module uses a strict JSON schema for data extraction:

.. code-block:: json

    {
      "supplier": {
        "name": "Supplier Name",
        "vat": "B12345678",
        "email": "supplier@example.com",
        "phone": "+34 666 777 888",
        "street": "Street Address",
        "city": "City",
        "zip": "28001",
        "country_code": "ES"
      },
      "invoice": {
        "supplier_invoice_number": "FAC-2025-001",
        "invoice_date": "2025-10-01",
        "due_date": "2025-11-01",
        "currency": "EUR",
        "payment_terms": "30 days",
        "notes": "Additional notes"
      },
      "lines": [
        {
          "description": "Product or service description",
          "quantity": 10.0,
          "uom": "Units",
          "unit_price": 100.0,
          "taxes": ["IVA 21%"],
          "product_code": "PROD001",
          "analytic_tags": []
        }
      ],
      "totals": {
        "untaxed": 1000.0,
        "tax": 210.0,
        "total": 1210.0
      },
      "meta": {
        "language": "es",
        "detected_country": "Spain",
        "pages_processed": 1
      }
    }

Tax Mapping
-----------

The module intelligently maps extracted tax names to Odoo taxes:

* "IVA 21%" → Searches for 21% purchase tax
* "IVA 10%" → Searches for 10% purchase tax
* "IVA 4%" → Searches for 4% purchase tax
* Generic search by name for other taxes

If no tax is found, the line is created without taxes (can be added manually).

Supplier Matching
-----------------

Suppliers are matched in this order:

1. By normalized VAT (removes spaces, dots, hyphens)
2. By name (case-insensitive)
3. If not found and "Create Partner if Missing" is enabled, creates new supplier

Total Validation
----------------

After creating the invoice, totals are validated:

* If difference between AI totals and calculated totals exceeds tolerance
* An error is raised and the invoice is left in draft for manual review

Security & Privacy
==================

GDPR Compliance
---------------

* Logs do not contain sensitive invoice data
* Original file attachment is optional (disabled if GDPR sensitive)
* Minimal data retention in job history
* API calls go directly to OpenAI (no intermediate storage)

Permissions
-----------

* **Invoice/Billing**: Can import invoices and view job history
* **Billing Manager**: Can delete job history

Models
======

xtendoo.invoice.ai.wizard
-------------------------

Transient model for the import wizard.

xtendoo.invoice.ai.job
----------------------

Persistent model storing import job history with metrics.

Known Limitations
=================

* Requires OpenAI API key (paid service)
* Token costs apply per API call (depends on file size and pages)
* Very complex invoices may require manual review
* Handwritten invoices may have lower accuracy
* OCR quality depends on image resolution

Bug Tracker
===========

Bugs are tracked on GitHub Issues. If you find a bug, please report it there.

Credits
=======

Authors
-------

* Xtendoo

Contributors
------------

* Xtendoo Development Team

Maintainer
----------

This module is maintained by Xtendoo.

License
=======

AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

