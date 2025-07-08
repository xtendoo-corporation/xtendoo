# Portal de Empleados (xtendoo_employee_portal)

## Descripción

Este módulo proporciona un portal web específico para empleados, donde pueden iniciar sesión usando un PIN de 4 dígitos y acceder a las siguientes funcionalidades:

1. **Fichar entrada y salida**: Los empleados pueden registrar sus entradas y salidas laborales.
2. **Gestión de ausencias**: Visualización y solicitud de ausencias (vacaciones, permisos, etc.).
3. **Planificaciones**: Visualización de su calendario laboral y horarios planificados.
4. **Partes de horas**: Acceso a sus registros de tiempo en proyectos y tareas.
5. **Registros de entrada y salida**: Historial completo de fichajes.

## Características

- Autenticación mediante PIN de 4 dígitos
- Interfaz responsive compatible con dispositivos móviles
- Menú simplificado con acceso exclusivo a las funcionalidades autorizadas
- Seguridad mediante tokens de sesión
- Integración completa con los módulos de RRHH de Odoo

## Requisitos

- Odoo 18.0
- Módulos de RRHH: hr, hr_attendance, hr_holidays, hr_timesheet, hr_work_entry

## Instalación

1. Clonar el repositorio en la carpeta de addons de Odoo
2. Actualizar la lista de aplicaciones
3. Instalar el módulo "Portal de Empleados"

## Configuración

Después de instalar el módulo:

1. Ir a Empleados > Configuración > Empleados
2. Seleccionar un empleado y asignarle un PIN de 4 dígitos en la pestaña "Configuración de RRHH"
3. El portal estará disponible en: /employee/portal/login

## Autor

Desarrollado por [Xtendoo](https://xtendoo.es)

## Licencia

AGPL-3.0
