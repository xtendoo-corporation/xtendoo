# Reproduce el caso real que motivó este módulo: un empleado con turno partido
# nocturno (p.ej. 22:00 a 07:00) al que Odoo contabilizaba prácticamente toda la
# jornada como hora extra, porque el calendario reparte ese turno en dos tramos
# situados en días de la semana distintos (un tramo no puede pasar de las 24h).
from datetime import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestNightShiftOvertime(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Night Shift Test Co',
            'attendance_overtime_validation': 'no_validation',
            'overtime_company_threshold': 0,
            'overtime_employee_threshold': 0,
        })
        cls.company.resource_calendar_id.tz = 'UTC'

        # Turno partido nocturno: lunes 22:00-23:59 + martes 00:00-01:00 (descanso)
        # y 01:01-07:00, igual que el calendario real que dispara el problema.
        cls.night_calendar = cls.env['resource.calendar'].create({
            'name': 'Turno noche 22h a 7h',
            'company_id': cls.company.id,
            'tz': 'UTC',
            'attendance_ids': [
                (0, 0, {
                    'name': 'Lunes noche',
                    'dayofweek': '0',
                    'hour_from': 22,
                    'hour_to': 23.983333333333334,
                    'day_period': 'afternoon',
                }),
                (0, 0, {
                    'name': 'Martes noche - descanso',
                    'dayofweek': '1',
                    'hour_from': 0,
                    'hour_to': 1,
                    'day_period': 'lunch',
                }),
                (0, 0, {
                    'name': 'Martes noche - mañana',
                    'dayofweek': '1',
                    'hour_from': 1.0166666666666666,
                    'hour_to': 7,
                    'day_period': 'morning',
                }),
            ],
        })

        # Calendario normal (de día) usado como control para comprobar que no
        # se modifica el cálculo cuando el turno no cruza la medianoche.
        cls.day_calendar = cls.env['resource.calendar'].create({
            'name': 'Turno de dia',
            'company_id': cls.company.id,
            'tz': 'UTC',
            'attendance_ids': [
                (0, 0, {'name': 'Mañana', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Comida', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tarde', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            ],
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Empleado Turno Noche',
            'company_id': cls.company.id,
            'tz': 'UTC',
            'resource_calendar_id': cls.night_calendar.id,
        })

    def _create_attendance(self, check_in, check_out):
        return self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        })

    def _overtime_duration(self, date_):
        overtime = self.env['hr.attendance.overtime'].search([
            ('employee_id', '=', self.employee.id),
            ('date', '=', date_),
        ])
        return sum(overtime.mapped('duration'))

    def test_overnight_shift_exact_schedule_has_no_spurious_overtime(self):
        """Fichaje exacto al turno previsto: la hora extra debe ser ~0, no ~8h."""
        self._create_attendance(
            datetime(2024, 1, 1, 22, 0, 0),   # lunes 22:00
            datetime(2024, 1, 2, 7, 0, 0),    # martes 07:00
        )
        duration = self._overtime_duration(datetime(2024, 1, 1).date())
        self.assertLess(
            abs(duration), 0.1,
            "El turno partido nocturno no debería generar horas extra si se ficha "
            "exactamente el horario previsto (se obtuvo %.4f)" % duration,
        )

    def test_overnight_shift_extra_time_is_counted_correctly(self):
        """Si entra antes y sale después del turno, la extra debe reflejar solo ese exceso."""
        self._create_attendance(
            datetime(2024, 1, 1, 21, 30, 0),  # 30 min antes de las 22:00
            datetime(2024, 1, 2, 7, 20, 0),   # 20 min después de las 07:00
        )
        duration = self._overtime_duration(datetime(2024, 1, 1).date())
        # ~50 minutos de exceso real (30 antes + 20 después), no las ~8h del turno.
        self.assertAlmostEqual(duration, 50 / 60, delta=0.05)

    def test_overnight_shift_short_shift_gives_negative_overtime(self):
        """Si ficha menos tiempo del previsto, debe verse como déficit, no como extra positiva."""
        self._create_attendance(
            datetime(2024, 1, 1, 22, 0, 0),
            datetime(2024, 1, 2, 5, 0, 0),  # sale 2h antes de las 07:00
        )
        duration = self._overtime_duration(datetime(2024, 1, 1).date())
        self.assertAlmostEqual(duration, -2, delta=0.1)

    def test_forgotten_checkout_multi_day_keeps_original_calculation(self):
        """Un fichaje anómalo de varios días (olvido de marcar salida) no debe tratarse
        como turno nocturno: debe seguir el cálculo original de Odoo (todo lo que
        sobrepasa el primer día previsto cuenta como extra), igual que antes de este
        módulo. Reproduce el escenario de
        TestHrAttendanceOvertime.test_refuse_timeoff del núcleo de hr_attendance."""
        self.employee.resource_calendar_id = self.day_calendar
        self._create_attendance(
            datetime(2024, 1, 1, 8, 0, 0),   # lunes 08:00
            datetime(2024, 1, 2, 16, 0, 0),  # martes 16:00 (32h después)
        )
        duration = self._overtime_duration(datetime(2024, 1, 1).date())
        self.assertAlmostEqual(duration, 23, delta=0.1)

    def test_same_day_shift_is_not_affected(self):
        """Un turno normal que no cruza medianoche mantiene el cálculo original de Odoo."""
        self.employee.resource_calendar_id = self.day_calendar
        self._create_attendance(
            datetime(2024, 1, 1, 8, 0, 0),
            datetime(2024, 1, 1, 19, 0, 0),  # 10h trabajadas (11h - 1h comida) vs 8h previstas
        )
        duration = self._overtime_duration(datetime(2024, 1, 1).date())
        self.assertAlmostEqual(duration, 2, delta=0.01)
