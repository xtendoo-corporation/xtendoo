===============================
Xtendoo Account Payment Effects
===============================

This module adds customer collection effects (checks, promissory notes, etc.)
management for Odoo 19, on top of core ``account`` only. It does not depend on
any OCA or Enterprise module.

Features
========

* Extends ``account.payment`` and ``account.payment.method.line`` (core
  models only).
* Adds a lightweight ``account.payment.remesa`` model (two states: draft and
  confirmed) to group collection-effect payments and deposit them in a bank
  journal in a single action.
* Keeps invoices in ``in_payment`` until the remesa is confirmed, using the
  standard core hook ``account.move._get_invoice_in_payment_state()``.
* Confirming a remesa creates one ``account.bank.statement.line`` for the
  total and reconciles it against the outstanding-account lines of every
  payment in the remesa, using only core reconciliation APIs
  (``account.move.line.reconcile()``). Invoices then flip to ``paid``
  automatically through Odoo's native ``payment_state`` computation.
* Creates a remesa from existing payments without recreating them.
* Protects existing payments when rejecting/canceling already-matched
  effects.

Dependencies
============

* ``account`` (core only)

Configuration
=============

1. Go to ``Accounting -> Configuration -> Journals``, open the bank journal
   used for the collection method (e.g. the "Pagaré" journal).
2. In the ``Incoming Payments`` tab, add or edit a payment method line.
3. Set an ``Outstanding Receipts account`` (``payment_account_id``).
4. Enable ``Efecto de cobro`` (``xtd_manage_effects``).
5. Enable ``Referencia obligatoria`` / ``Vencimiento obligatorio`` as needed.

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

Usage
=====

Register a check/promissory note from an invoice
--------------------------------------------------

1. Open a customer invoice.
2. Click ``Register Payment``.
3. Choose an effect-enabled payment method.
4. Enter the effect reference and due date when applicable.
5. Create the payment.

The payment is posted to the configured outstanding receipt account and the
invoice remains ``in_payment`` until the remesa that includes it is
confirmed.

Consult collection effects
--------------------------

Open ``Accounting -> Customers -> Efectos en cartera``.
Use the provided filters to distinguish:

* In portfolio.
* Deposited (assigned to a draft remesa).
* Collected (remesa confirmed / matched with the bank).
* Rejected.
* Canceled.
* Overdue / due today / upcoming / without due date.

Create and confirm a remesa
----------------------------

1. Open ``Accounting -> Customers -> Remesas de efectos`` and create a new
   remesa: set its payment method and the destination bank journal.
2. In the ``Pagos`` tab, click ``Add a line`` and pick the eligible payments
   (same company, currency and payment method, not already in a remesa, not
   yet matched).
3. Click ``Confirmar remesa``.

This creates one bank statement line for the total and reconciles it against
all the selected payments in a single step: the payments become
``is_matched = True`` and every fully-paid invoice becomes ``paid``.

Alternatively, from ``Efectos en cartera`` select existing payments and run
``Crear remesa`` from the action menu to pre-fill a draft remesa with them.

Undo a confirmation
--------------------

If a remesa was confirmed by mistake and its bank line has not been touched
by anything else, open it and click ``Volver a borrador``. This removes the
reconciliation, deletes the generated bank statement line, and puts the
remesa (and its invoices) back to how they were before confirming.

Returned / rejected effects
===========================

* If the effect has not been matched with a bank transaction yet
  (``is_matched = False``), use the standard ``Reject`` button on the
  payment. This only sets ``state = rejected``; no journal entry is deleted.
* If the effect is already matched (``is_matched = True``), the module
  blocks both ``Reject`` and ``Cancel`` directly on the payment: it has
  already been deposited and reconciled against a real bank movement, so
  rejecting or cancelling it without undoing that first would leave the
  books inconsistent. Reverse the bank matching first (reset the remesa to
  draft, which removes the reconciliation and deletes the generated bank
  statement line), then reject or cancel the payment.

Limitations
===========

* One remesa always has one company, one currency, one bank journal and one
  payment method line; it groups payments sharing all four. Payments using a
  different payment method or destined to a different journal need a
  separate remesa.
* No export file (SEPA or similar) is generated; this module only covers
  physical collection effects (pagarés, cheques) deposited as a single bank
  movement.
