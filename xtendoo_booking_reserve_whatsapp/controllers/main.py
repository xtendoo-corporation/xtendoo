from odoo.addons.xtendoo_booking_reserve.controllers.main import BookingReserveController

class BookingReserveControllerWhatsApp(BookingReserveController):
    
    def booking_reserve(self, **data):
        # We override to extract whatsapp_opt_in before calling logic, or modify logic?
        # The base method reads fields one by one. It doesn't use **data blindly for create.
        # It does: `request_vals = { ... }`
        # So we must override the method completely or monkey patch?
        # Since it's a controller, inheritance works if we call super but super returns response.
        # The base method CREATES the record.
        # We want to add a field to creation.
        
        # Option 1: Copy-paste override (cleanest for functionality, bad for maintenance).
        # Option 2: Pre-process data? No, base method constructs dict explicitly.
        # Option 3: Call super, then update record?
        # Base returns `request.make_response(...)` (JSON).
        # But inside it creates `booking_request`.
        # We can't easily intercept the created record unless we fetch it again?
        # The base response contains `request_id`.
        # So we can call super, parse response, invalid if needed, else update `booking.request`.
        
        response = super().booking_reserve(**data)
        
        # Parse response to see if success
        # response is a werkzeug Response object because we returned request.make_response(json.dumps(...))
        # This makes it hard to parse.
        
        # Actually, standard Odoo controllers often return just the data result for JSON routes, 
        # but here we changed it to `type='http'` returning `json.dumps`.
        # This makes inheritance painful.
        
        # Let's inspect data BEFORE super?
        # We can't inject into super's internal `request_vals`.
        
        # So we must COPY-PASTE override or Refactor base module to allow extension.
        # Given constraints, I will Copy-Paste override but cleaner:
        # Actually, wait. I can just update the record AFTER super if I know the ID.
        # But reading the response body of a Response object is possible.
        
        # However, checking `request_id` from JSON response:
        try:
            if response.data:
                import json
                result = json.loads(response.data)
                if result.get('success') and result.get('request_id'):
                    req_id = result['request_id']
                    whatsapp_opt_in = data.get('whatsapp_opt_in')
                    
                    # Convert JS boolean/string to python boolean
                    if whatsapp_opt_in in ['true', 'True', True, '1', 1]:
                        val = True
                    else:
                        val = False
                        
                    if val:
                        # Update the record
                        from odoo import http
                        request_obj = http.request.env['booking.request'].sudo().browse(req_id)
                        if request_obj.exists():
                            request_obj.write({'whatsapp_opt_in': True})
                            # Trigger partner update logic explicitly if needed, but we put it in `create` too?
                            # In `booking_request.py`, we put logic in `_get_or_create_partner`.
                            # Only if `self.whatsapp_opt_in` is setup.
                            # Since we update it AFTER create (here), we might miss the initial partner creation hook if it runs in create.
                            # `create` calls `_notify_new_request`.
                            # `action_approve` calls `_get_or_create_partner`.
                            # Since `action_approve` happens later (manual), updating `whatsapp_opt_in` here is FINE.
                            # It will be ready when admin clicks Approve.
        except Exception:
            pass # Fallback, don't break flow
            
        return response
