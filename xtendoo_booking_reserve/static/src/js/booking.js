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
        this.$el.addClass('d-none');
        document.getElementById('booking_step_2').classList.remove('d-none');
        // Inicializar el calendario visual si no está ya
        if (!window.bookingCalendarInitialized) {
            window.bookingCalendarInitialized = true;
            if (publicWidget.registry.BookingCalendar) {
                new publicWidget.registry.BookingCalendar();
            }
        }
    },
});

publicWidget.registry.BookingCalendar = publicWidget.Widget.extend({
    selector: '#booking_step_2',
    events: {
        'click #booking_reserve': '_onReserve',
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
                    result.forEach(hour => {
                        const opt = document.createElement('option');
                        opt.value = hour;
                        opt.textContent = hour;
                        hourSelect.appendChild(opt);
                    });
                    hourSelect.disabled = false;
                    hourSelect.parentElement.classList.remove('d-none');
                    document.getElementById('selected_date').value = dateStr;
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
    _onReserve: function () {
        const form = document.getElementById('booking_form_step_1');
        const type_id = form.querySelector('[name="booking_type"]').value;
        const name = form.querySelector('[name="name"]').value;
        const phone = form.querySelector('[name="phone"]').value;
        const email = form.querySelector('[name="email"]').value;
        const date = document.getElementById('selected_date').value;
        const hour = document.getElementById('booking_hour').value;
        
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
                    alert(result.message || 'Su solicitud ha sido enviada y será revisada pronto.');
                    window.location.reload();
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
