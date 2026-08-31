===============================
Xtendoo Account Payment Effects
===============================

This module adds customer collection effects management on top of OCA payment
orders/lots for Odoo 19 Community.

Features
========

* Reuses ``account.payment``, ``account.payment.order`` and ``account.payment.lot``.
* Supports checks, promissory notes and future collection instruments through
  payment method line configuration.
* Keeps invoices in ``in_payment`` until the bank statement matches the payment.
* Creates deposit/remittance lots from existing payments without recreating them.
* Adds payment lot selection to OCA bank reconciliation.
* Protects existing payments when canceling Xtendoo lots/orders.

Dependencies
============

* ``account_payment_batch_oca``
* ``account_reconcile_oca``

Configuration
=============

1. Go to ``Accounting -> Configuration -> Payment Methods``.
2. Create or edit an inbound payment method line.
3. Enable ``Selectable on Payment Orders``.
4. Enable ``Manage as Collection Effect``.
5. Configure an outstanding receipt account in ``Outstanding Receipt Account``.
6. Enable reference and due date requirements as needed.

Example: Check
==============

* Payment type: Inbound
* Manage as Collection Effect: enabled
* Effect Reference Required: enabled
* Effect Due Date Required: disabled

Example: Promissory Note
========================

* Payment type: Inbound
* Manage as Collection Effect: enabled
* Effect Reference Required: enabled
* Effect Due Date Required: enabled

Outstanding receipt accounts
============================

Do not create custom accounting logic in this module. Configure the outstanding
receipt account directly on ``account.payment.method.line.payment_account_id``.
Typical examples are portfolio checks or promissory notes accounts.

Usage
=====

Register a check from an invoice
--------------------------------

1. Open a customer invoice.
2. Click ``Register Payment``.
3. Choose an effect-enabled payment method.
4. Enter the effect reference and due date when applicable.
5. Create the payment.

The payment is posted to the configured outstanding receipt account and the
invoice remains ``in_payment`` until the bank statement is reconciled.

Consult collection effects
--------------------------

Open ``Accounting -> Customers -> Collection Effects``.
Use the provided filters to distinguish:

* In portfolio.
* Deposited/remitted.
* Collected.
* Rejected.
* Canceled.
* Overdue / due today / upcoming / without due date.

Create a deposit/remittance lot
-------------------------------

1. Open ``Collection Effects``.
2. Select existing inbound customer payments managed as effects.
3. Run ``Create Deposit/Remittance Lot`` from the action menu.
4. Confirm the wizard.

The module creates one ``account.payment.order`` with
``xtd_source_type = existing_payments`` and one related ``account.payment.lot``.
No new payments and no new journal entries are created.

Reconcile a lot
---------------

1. Create or import the bank statement line for the deposit.
2. Open the OCA reconciliation form.
3. Go to the ``Payment Lots`` tab.
4. Select the lot.
5. Validate the reconciliation.

The payment liquidity lines are added as counterparts. Once reconciliation is
complete, payments become matched and invoices move from ``in_payment`` to
``paid`` through standard Odoo reconciliation.

Cancel a lot safely
-------------------

If the lot has no matched payments yet, open the related payment order or lot
and use ``Cancel Lot``.

This operation:

* removes ``payment_lot_id`` from payments,
* removes ``payment_order_id`` from payments,
* deletes the OCA lot structure,
* keeps the original payments,
* keeps the posted journal entries,
* keeps the invoice/payment reconciliation intact.

Returned / rejected effects
===========================

Use the standard payment rejection state (``rejected``). Do not alter
reconciliation tables with SQL. If a bank reconciliation already exists, undo
it first through standard Odoo/OCA flows and then reject the payment.

Difference between is_reconciled and is_matched
===============================================

* ``is_reconciled`` means the payment has been reconciled against the invoice
  receivable/payable side.
* ``is_matched`` means the payment liquidity side has been matched with the bank
  statement or equivalent bank-side reconciliation.

Therefore, an effect can already be reconciled with the invoice while still not
matched with the bank. That is why the invoice stays ``in_payment`` before the
bank matching and becomes ``paid`` only afterwards.

Limitations
===========

* One Xtendoo lot currently supports one company, one currency, one journal and
  one payment method line.
* Mixed methods (for example check + promissory note) are intentionally blocked.
* The module relies on OCA reconciliation UI and does not add custom JS.

