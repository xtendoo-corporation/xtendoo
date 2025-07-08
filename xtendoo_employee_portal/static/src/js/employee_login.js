/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class EmployeeLoginForm extends Component {
    setup() {
        this.pinInput = null;
    }

    /**
     * Limita la entrada a solo dígitos y máximo 4
     * @param {Event} ev
     */
    onPinInput(ev) {
        const input = ev.target;
        // Eliminar caracteres que no sean dígitos
        input.value = input.value.replace(/\D/g, '');
        // Limitar a 4 dígitos
        if (input.value.length > 4) {
            input.value = input.value.slice(0, 4);
        }
    }

    /**
     * Validación al enviar el formulario
     * @param {Event} ev
     */
    onSubmit(ev) {
        const input = ev.target.querySelector('input[name="pin"]');
        if (!input.value || input.value.length !== 4) {
            ev.preventDefault();
            alert('El PIN debe contener 4 dígitos.');
            return false;
        }
    }
}

EmployeeLoginForm.template = "xtendoo_employee_portal.employee_login_form";

// Registrar el componente para uso en el frontend
registry.category("public_components").add("EmployeeLoginForm", EmployeeLoginForm);

// Funcionalidad para elementos existentes en el DOM
document.addEventListener('DOMContentLoaded', function() {
    const pinForms = document.querySelectorAll('.js_employee_pin_form');

    pinForms.forEach(form => {
        const pinInput = form.querySelector('input[name="pin"]');

        if (pinInput) {
            pinInput.addEventListener('input', function(ev) {
                // Eliminar caracteres que no sean dígitos
                this.value = this.value.replace(/\D/g, '');
                // Limitar a 4 dígitos
                if (this.value.length > 4) {
                    this.value = this.value.slice(0, 4);
                }
            });
        }

        form.addEventListener('submit', function(ev) {
            const input = this.querySelector('input[name="pin"]');
            if (!input.value || input.value.length !== 4) {
                ev.preventDefault();
                alert('El PIN debe contener 4 dígitos.');
                return false;
            }
        });
    });
});
