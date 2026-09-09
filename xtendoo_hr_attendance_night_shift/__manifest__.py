{
    "name": "HR Attendance Night Shift Overtime Fix",
    "version": "18.0.1.0.0",
    "category": "Human Resources/Attendances",
    "summary": "Corrige el cálculo de horas extra para turnos que cruzan la medianoche (turno partido nocturno)",
    "description": """
        El motor de horas extra de Asistencias (hr_attendance) calcula las horas
        previstas de cada jornada agrupando los tramos del calendario por el día
        en que empieza cada tramo, mientras que las horas realmente fichadas se
        atribuyen enteras al día del "check in".

        Para un turno que cruza la medianoche (p.ej. 22:00 a 07:00), el calendario
        se modela obligatoriamente en dos tramos situados en días distintos. Esa
        diferencia de criterio hace que Odoo compare el fichaje completo (~8h)
        contra solo la parte del tramo anterior a medianoche, contabilizando como
        hora extra prácticamente toda la jornada.

        Este módulo corrige el cálculo únicamente para los fichajes cuya entrada
        y salida caen en días distintos (turnos nocturnos), comparando las horas
        trabajadas contra las horas previstas por el calendario para ese turno
        completo. El cálculo de jornadas normales (que no cruzan medianoche) no
        se modifica.
    """,
    "author": "Xtendoo",
    "website": "https://www.xtendoo.com",
    "license": "LGPL-3",
    "depends": ["hr_attendance"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
