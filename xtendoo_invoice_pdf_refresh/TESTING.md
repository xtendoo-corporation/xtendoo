# Copyright 2026 Xtendoo - Manuel Calero
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

"""
Manual Testing Guide for xtendoo_invoice_pdf_refresh

This is not an automated test but a guide for manual testing.
For automated tests, you would need to create a proper test file.
"""

# MANUAL TEST SCENARIO
# ====================

"""
Scenario 1: Customer Invoice PDF Refresh
-----------------------------------------

1. Create a new customer invoice:
   - Go to Invoicing > Customers > Invoices
   - Create new invoice
   - Add customer: Any customer
   - Add invoice line: Product A, Qty: 10, Price: 100.00
   - Total should be: 1,000.00 (+ taxes)

2. Post the invoice:
   - Click "Confirm" button
   - State should change to "Posted"

3. Generate PDF (cache it):
   - Click "Print" > "Invoice"
   - PDF is generated and cached as attachment
   - Note: Total = 1,000.00

4. Verify attachment exists:
   - Go to Settings > Technical > Attachments
   - Filter by: res_model = 'account.move'
   - Find the PDF for your invoice
   - Name should be like: "INV/2024/00001.pdf"

5. Reset to Draft:
   - Go back to the invoice
   - Click "Reset to Draft" button
   - State should change to "Draft"

6. Verify PDF attachment deleted:
   - Go back to Settings > Technical > Attachments
   - The PDF attachment should be GONE
   - This proves the module is working!

7. Edit the invoice:
   - Change quantity from 10 to 20
   - New total should be: 2,000.00 (+ taxes)

8. Post again:
   - Click "Confirm" button

9. Generate PDF again:
   - Click "Print" > "Invoice"
   - PDF should show NEW total: 2,000.00
   - This proves the PDF was refreshed!

Expected Result: ✅ PDF shows updated amount (2,000.00)
If Failed: ❌ PDF still shows old amount (1,000.00)


Scenario 2: Vendor Bill PDF Refresh
------------------------------------

Follow same steps but with:
- Invoicing > Vendors > Bills
- Create vendor bill instead of customer invoice


Scenario 3: Verify User Uploads NOT Deleted
--------------------------------------------

1. Create and post invoice (as in Scenario 1)

2. Upload a manual PDF:
   - In invoice form, click on Attachment icon (📎)
   - Upload a PDF file (any PDF)
   - Give it a name like: "my_custom_document.pdf"

3. Reset to Draft:
   - Click "Reset to Draft"

4. Verify:
   - Go to Settings > Technical > Attachments
   - Your custom PDF should STILL EXIST
   - Only system-generated invoice PDF should be deleted

Expected Result: ✅ Custom upload preserved
If Failed: ❌ Custom upload was deleted (BUG!)


Scenario 4: Check Logs
-----------------------

1. Follow Scenario 1 steps 1-5 (create, post, reset)

2. Check Odoo logs:
   docker-compose logs -f odoo | grep "Clearing.*cached invoice PDF"

3. You should see messages like:
   "Clearing 1 cached invoice PDF(s) for INV/2024/00001: INV/2024/00001.pdf"

Expected Result: ✅ Log message appears
If Failed: ❌ No log message (module not working)


Performance Test
----------------

Create 100 invoices, post them, reset them all at once:
- Time should be reasonable (< 10 seconds for 100 invoices)
- No database locks or errors

Expected Result: ✅ Fast bulk processing
If Failed: ❌ Timeouts or errors


Edge Cases to Test
------------------

1. Invoice without number:
   - Draft invoice never posted → No PDF to delete → Should work fine

2. Multiple PDFs:
   - Post invoice, print twice → May create multiple attachments
   - Reset → All matching PDFs should be deleted

3. Multi-company:
   - Create invoices in Company A and Company B
   - Reset both → Each should only delete its own PDFs

4. Different invoice types:
   - Test with: out_invoice, out_refund, in_invoice, in_refund
   - All should work

5. Journal entries (non-invoices):
   - Create misc journal entry
   - Reset to draft → Should NOT trigger PDF deletion (not an invoice)


Debugging Tips
--------------

If module doesn't work:

1. Check module installed:
   Apps > Search "invoice_pdf_refresh" > Should show "Installed"

2. Check inheritance working:
   Settings > Technical > Models
   Search: account.move
   Should show: xtendoo_invoice_pdf_refresh.models.account_move

3. Enable debug logging:
   Add to odoo.conf:
   log_handler = :INFO,odoo.addons.xtendoo_invoice_pdf_refresh:DEBUG

4. Test method directly in shell:
   docker-compose exec odoo odoo shell -d YOUR_DB
   >>> invoice = env['account.move'].browse(123)  # Your invoice ID
   >>> invoice._xtd_unlink_cached_invoice_pdfs()
   >>> # Check if PDFs deleted
"""
