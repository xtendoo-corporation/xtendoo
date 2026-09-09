from datetime import datetime, time, timedelta

import pytz

from odoo import models

# Duración máxima razonable de un turno para tratarlo como "turno nocturno partido".
# Por encima de esto (p.ej. un fichaje de 32h por un olvido de marcar salida) el
# fichaje ya no representa un turno real y debe seguir el cálculo original de Odoo,
# que premia como hora extra todo lo que sobrepasa el primer día (comportamiento ya
# cubierto por los tests del núcleo, p.ej. TestHrAttendanceOvertime.test_refuse_timeoff).
MAX_NIGHT_SHIFT_SPAN = timedelta(hours=20)


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    def _get_pre_post_work_time(self, employee, working_times, attendance_date):
        """Corrige el cálculo de horas extra para turnos nocturnos que cruzan la medianoche.

        El cómputo original agrupa las horas previstas del calendario (``working_times``)
        por el día en el que empieza cada tramo, mientras que un fichaje completo se
        atribuye entero al día del check-in (ver ``_update_overtime``/``_get_attendances_dates``).
        Un turno partido nocturno (p.ej. 22:00-07:00) se modela obligatoriamente en dos
        tramos de calendario en días distintos, porque un tramo no puede pasar de las 24h.
        Eso hace que el cálculo original compare el fichaje completo (~8h) solo contra el
        tramo previo a medianoche del día de entrada, contando casi toda la jornada como
        hora extra.

        Para los fichajes cuya entrada y salida caen en días distintos y cuya duración es
        la de un turno real (ver ``MAX_NIGHT_SHIFT_SPAN``), se comparan aquí las horas
        trabajadas contra las horas de calendario previstas para todo el rango de días que
        cubre el turno (el día de entrada y el de salida en la zona horaria del empleado),
        en vez de depender del reparto por día de ``working_times``. Se usa el rango de días
        completo -y no [check_in, check_out]- para que un fichaje corto (entrada tardía o
        salida anticipada) siga comparándose contra el turno completo previsto y produzca un
        déficit, en lugar de reducir también las horas previstas.

        El resto de fichajes (que no cruzan medianoche, o cruzan pero duran demasiado para
        ser un turno real) siguen el cálculo original sin cambios.
        """
        employee_tz = pytz.timezone(employee._get_tz())

        def _local_date(dt):
            return pytz.utc.localize(dt).astimezone(employee_tz).date()

        def _is_night_shift(attendance):
            return (
                attendance.check_out
                and _local_date(attendance.check_in) != _local_date(attendance.check_out)
                and (attendance.check_out - attendance.check_in) <= MAX_NIGHT_SHIFT_SPAN
            )

        night_shifts = self.filtered(_is_night_shift)
        other_attendances = self - night_shifts

        pre_work_time = work_duration = post_work_time = planned_work_duration = 0.0
        if other_attendances:
            pre_work_time, work_duration, post_work_time, planned_work_duration = super(
                HrAttendance, other_attendances
            )._get_pre_post_work_time(employee, working_times, attendance_date)

        for attendance in night_shifts:
            day_start = employee_tz.localize(datetime.combine(_local_date(attendance.check_in), time.min))
            day_stop = employee_tz.localize(datetime.combine(_local_date(attendance.check_out), time.max))
            scheduled_intervals = employee._employee_attendance_intervals(day_start, day_stop)
            scheduled_duration = sum(
                (interval[1] - interval[0]).total_seconds() / 3600.0
                for interval in scheduled_intervals
            )
            work_duration += attendance.worked_hours
            planned_work_duration += scheduled_duration

        return pre_work_time, work_duration, post_work_time, planned_work_duration
