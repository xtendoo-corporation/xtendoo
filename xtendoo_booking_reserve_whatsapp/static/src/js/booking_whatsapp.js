/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';
import '@xtendoo_booking_reserve/js/booking'; // Ensure base module is loaded

// Patch or extend BookingCalendar?
// Since BookingCalendar is a widget instance, we can include methods or override them if we re-register or use include.
// In Odoo 16+, include is common for widgets.

publicWidget.registry.BookingCalendar.include({
    _onReserve: function () {
        // We override to add whatsapp_opt_in to the data payload
        // This is a bit copy-paste because we can't easily hook into the middle of the function 
        // unless we refactor base module.
        // But we can call super? super _onReserve calls ajax.
        // We need to inject data into the AJAX call.
        // If we can't inject, we must copy-paste logic.
        
        // Let's copy logic but add the field.
        const clientForm = document.getElementById('client_data_form');
        if (!clientForm.checkValidity()) {
            clientForm.reportValidity();
            return;
        }

        const form = document.getElementById('booking_form_step_1');
        const type_id = form.querySelector('[name="booking_type"]').value;
        const name = clientForm.querySelector('[name="name"]').value;
        const phone = clientForm.querySelector('[name="phone"]').value;
        const email = clientForm.querySelector('[name="email"]').value;
        
        // NEW: Checkbox
        const whatsapp_opt_in = clientForm.querySelector('[name="whatsapp_opt_in"]').checked;
        
        const date = document.getElementById('selected_date').value;
        const hour = document.getElementById('booking_hour').value;
        
        if (!hour) {
             alert("Por favor, selecciona una hora.");
             return;
        }
        
        const csrfTokenInput = document.querySelector('input[name="csrf_token"]');
        const csrfToken = csrfTokenInput ? csrfTokenInput.value : '';
        
        $.ajax({
            url: '/booking/reserve/submit',
            type: 'POST',
            dataType: 'json',
            data: {
                type_id: type_id,
                name: name,
                phone: phone,
                email: email,
                whatsapp_opt_in: whatsapp_opt_in, // Passed to controller
                date: date,
                hour: hour,
                csrf_token: csrfToken
            },
            success: function (response) {
                const result = response.result || response;
                if (result && result.success) {
                    // Update modal content - reusing ID from base
                    const msgElement = document.getElementById('booking_success_message');
                    if (msgElement) {
                        msgElement.textContent = result.message || 'Su solicitud ha sido enviada y será revisada pronto.';
                    }
                    
                    // Init and Show Modal (jQuery fallback)
                    const $modal = $('#booking_success_modal');
                    if ($modal.length) {
                         $modal.modal('show');
                        $modal.on('hidden.bs.modal', function () {
                            window.location.reload();
                        });
                        const okBtn = document.getElementById('btn_success_modal_ok');
                         if(okBtn) {
                             okBtn.addEventListener('click', function () {
                                $modal.modal('hide');
                            });
                         }
                    } else {
                        alert(result.message);
                        window.location.reload();
                    }
                    
                } else {
                    alert(result.message || 'Error al enviar la solicitud.');
                }
            },
            error: function (xhr, status, error) {
                console.error(xhr);
                let errorMessage = 'Error al enviar la solicitud.';
                if (xhr.responseText) {
                    try {
                        const json = JSON.parse(xhr.responseText);
                        if (json.message) errorMessage += '\n' + json.message;
                    } catch(e) {}
                }
                 alert(errorMessage);
            }
        });
    }
});
