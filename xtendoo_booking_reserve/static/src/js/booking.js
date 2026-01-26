/** @odoo-module **/
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.BookingReserve = publicWidget.Widget.extend({
    selector: '#booking_form_step_1',
    events: {
        'click #booking_next': '_onNext',
    },
    _onNext: function () {
        const form = this.$el[0];
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        const typeSelect = form.querySelector('[name="booking_type"]');
        const typeName = typeSelect.options[typeSelect.selectedIndex].text;
        document.getElementById('type_summary_step_2').textContent = typeName;
        
        this.$el.addClass('d-none');
        document.getElementById('booking_step_2').classList.remove('d-none');
    },
});

publicWidget.registry.BookingCalendar = publicWidget.Widget.extend({
    selector: '#booking_main_container',
    events: {
        'click #booking_to_step_3': '_onToStep3',
        'click #booking_back_step_2': '_onBackStep2',
        'click #booking_reserve': '_onReserve',
        'change #booking_hour': '_onHourChange',
    },
    start: function () {
        this.initCalendar();
    },
    initCalendar: function () {
        const self = this;
        const calendarEl = document.getElementById('booking_calendar');
        if (!calendarEl) return;
        const calendar = new window.FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            locale: 'es',
            selectable: true,
            height: 'auto',
            contentHeight: 'auto',
            aspectRatio: 1.35,
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: ''
            },
            dateClick: function (info) {
                self.onDateClick(info.dateStr);
            },
            datesSet: function (info) {
                if (self.calendar) {
                    self.calendar.updateSize();
                }
            },
            events: function (fetchInfo, successCallback, failureCallback) {
                const start = fetchInfo.startStr.slice(0, 10);
                const end = fetchInfo.endStr.slice(0, 10);
                
                // NO enviamos csrf_token aqui porque el controlador no tiene **kwargs y da warning
                $.ajax({
                    url: '/booking/availability',
                    type: 'POST',
                    dataType: 'json',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        params: {
                            type_id: document.querySelector('[name="booking_type"]').value,
                            start: start,
                            end: end
                        }
                    }),
                    success: function (response) {
                        const result = response.result || response;
                        if(Array.isArray(result)){
                             const events = result.map(day => ({
                                start: day.date,
                                display: 'background',
                                color: day.available ? '#b3e6b3' : '#e6e6e6',
                                allDay: true
                            }));
                            successCallback(events);
                        } else {
                            successCallback([]);
                        }
                    },
                    error: function () {
                        failureCallback();
                    }
                });
            },
        });
        calendar.render();
        self.calendar = calendar;

        const obs = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        self.calendar.updateSize();
                    }, 50);
                     setTimeout(() => {
                        self.calendar.updateSize();
                    }, 200);
                }
            });
        });
        obs.observe(calendarEl);
    },
    onDateClick: function (dateStr) {
        // Availability hours tampoco tiene **kwargs, asi que cuidado
        $.ajax({
            url: '/booking/availability/hours',
            type: 'POST',
            dataType: 'json',
            contentType: 'application/json',
            data: JSON.stringify({
                params: {
                    type_id: document.querySelector('[name="booking_type"]').value,
                    date: dateStr
                }
            }),
            success: function (response) {
                const result = response.result || response;
                if (Array.isArray(result) && result.length > 0) {
                    const hourSelect = document.getElementById('booking_hour');
                    hourSelect.innerHTML = '';
                    // Add default option
                    const defaultOpt = document.createElement('option');
                    defaultOpt.value = "";
                    defaultOpt.textContent = "Selecciona una hora";
                    defaultOpt.selected = true;
                    defaultOpt.disabled = true;
                    hourSelect.appendChild(defaultOpt);

                    result.forEach(hour => {
                        const opt = document.createElement('option');
                        opt.value = hour;
                        opt.textContent = hour;
                        hourSelect.appendChild(opt);
                    });
                    hourSelect.disabled = false;
                    hourSelect.parentElement.classList.remove('d-none');
                    document.getElementById('selected_date').value = dateStr;
                    
                    // Enable Next button if hour is already valid (though usually user must pick)
                    document.getElementById('booking_to_step_3').classList.remove('d-none');
                } else {
                    alert('No hay horas disponibles para esta fecha.');
                }
            },
            error: function (xhr) {
                 console.error(xhr);
                 alert('Error al consultar horas.');
            }
        });
    },
    
    _onHourChange: function() {
        const hour = document.getElementById('booking_hour').value;
        const btn = document.getElementById('booking_to_step_3');
        if(hour) {
             btn.classList.remove('d-none'); // Ensure visible
             // Could also enable if disabled
        }
    },

    _onToStep3: function() {
        const date = document.getElementById('selected_date').value;
        const hour = document.getElementById('booking_hour').value;
        
        if (!date || !hour) {
            alert('Por favor selecciona fecha y hora.');
            return;
        }
        
        // Populate Summary
        const typeSelect = document.querySelector('[name="booking_type"]');
        const typeName = typeSelect.options[typeSelect.selectedIndex].text;
        
        document.getElementById('summary_type_step_3').textContent = typeName;
        document.getElementById('summary_date_step_3').textContent = date;
        document.getElementById('summary_hour_step_3').textContent = hour;
        
        // Transition
        document.getElementById('booking_step_2').classList.add('d-none');
        document.getElementById('booking_step_3').classList.remove('d-none');
    },

    _onBackStep2: function() {
        document.getElementById('booking_step_3').classList.add('d-none');
        document.getElementById('booking_step_2').classList.remove('d-none');
        // Triggers resize in case
         if (this.calendar) {
            this.calendar.updateSize();
        }
    },

    _onReserve: function () {
        // Validate client form
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
        const date = document.getElementById('selected_date').value;
        const hour = document.getElementById('booking_hour').value;
        
        if (!hour) {
             alert("Por favor, selecciona una hora.");
             return;
        }
        
        // AQUI SI enviamos csrf_token porque booking_reserve acepta **data (kwargs)
        // obteniendolo del input hidden inyectado por el servidor
        const csrfTokenInput = document.querySelector('input[name="csrf_token"]');
        const csrfToken = csrfTokenInput ? csrfTokenInput.value : '';
        
        // Enviamos como form-data normal (type='http' en backend)
        $.ajax({
            url: '/booking/reserve/submit',
            type: 'POST',
            dataType: 'json',
            // No contentType json, usa default x-www-form-urlencoded
            data: {
                type_id: type_id,
                name: name,
                phone: phone,
                email: email,
                date: date,
                hour: hour,
                csrf_token: csrfToken
            },
            success: function (response) {
                const result = response.result || response;
                if (result && result.success) {
                    // Update modal content
                    document.getElementById('booking_success_message').textContent = result.message || 'Su solicitud ha sido enviada y será revisada pronto.';
                    
                    // Init and Show Modal (jQuery fallback for Odoo)
                    const $modal = $('#booking_success_modal');
                    $modal.modal('show');
                    
                    // Bind reload events
                    $modal.on('hidden.bs.modal', function () {
                        window.location.reload();
                    });
                    
                    document.getElementById('btn_success_modal_ok').addEventListener('click', function () {
                        $modal.modal('hide');
                    });
                    
                } else {
                    alert(result.message || 'Error al enviar la solicitud.');
                }
            },
            error: function (xhr, status, error) {
                console.error(xhr);
                let errorMessage = 'Error al enviar la solicitud.';
                if (xhr.responseText) {
                    // Try to extract message if it's JSON
                    try {
                        const json = JSON.parse(xhr.responseText);
                        if (json.message) errorMessage += '\n' + json.message;
                    } catch(e) {
                         // If HTML or other, just show generic
                         console.log("Response text:", xhr.responseText);
                    }
                }
                 alert(errorMessage + "\nCódigo: " + xhr.status + "\nVer consola para detalles.");
            }
        });
    }
});
