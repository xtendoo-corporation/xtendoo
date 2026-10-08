/** @odoo-module **/

import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";
import { useBus } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

const HOURS_EVENT = "XTD_CALENDAR:HOURS";
const pad = (n) => String(n).padStart(2, "0");

// "Mostrar todo" es temporal: se recuerda mientras dure la sesión del navegador.
const xtdHours = { showAll: false };

/** Franja horaria elegida por el usuario en sus preferencias (por defecto, todo el día). */
export function getUserHourRange() {
    const start = Number(user.settings?.xtd_calendar_hour_start ?? 0);
    const end = Number(user.settings?.xtd_calendar_hour_end ?? 24);
    return Number.isInteger(start) && Number.isInteger(end) && start >= 0 && start < end && end <= 24
        ? { start, end }
        : { start: 0, end: 24 };
}

function slotOptions() {
    const { start, end } = xtdHours.showAll ? { start: 0, end: 24 } : getUserHourRange();
    return { slotMinTime: `${pad(start)}:00:00`, slotMaxTime: `${pad(end)}:00:00` };
}

// Vistas de día y semana: franja horaria del usuario, apertura centrada en la
// hora actual y eventos cortos legibles.
patch(CalendarCommonRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        useBus(this.env.bus, HOURS_EVENT, () => {
            const api = this.fc?.api;
            if (api) {
                for (const [name, value] of Object.entries(slotOptions())) {
                    api.setOption(name, value);
                }
            }
        });
    },

    /**
     * Odoo marca como "no laborables" todos los días cuando el usuario no tiene
     * empleado con horario (el caso del administrador en muchas bases): toda la
     * rejilla sale gris y no aporta información. Si no hay ni un solo día
     * laborable en el rango visible, no se sombrea nada.
     */
    getDayCellClassNames(info) {
        const classes = super.getDayCellClassNames(...arguments);
        return classes.length && this.xtdEveryDayIsUnusual() ? [] : classes;
    },

    xtdEveryDayIsUnusual() {
        const { rangeStart, rangeEnd, unusualDays } = this.props.model;
        if (!rangeStart || !rangeEnd || !unusualDays?.length) {
            return false;
        }
        const unusual = new Set(unusualDays);
        const days = Math.min(Math.ceil(rangeEnd.diff(rangeStart, "days").days), 62);
        for (let i = 0; i < days; i++) {
            if (!unusual.has(rangeStart.plus({ days: i }).toISODate())) {
                return false;
            }
        }
        return true;
    },

    get options() {
        const options = super.options;
        const startHour = Math.max(luxon.DateTime.local().hour - 2, 0);
        return {
            ...options,
            ...slotOptions(),
            scrollTime: `${pad(startHour)}:00:00`,
            scrollTimeReset: false,
            eventMinHeight: 22,
        };
    },
});

// Aviso flotante cuando la franja elegida deja fuera algún evento: nunca se
// ocultan citas sin avisar.
patch(CalendarRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.xtdHoursState = useState({ showAll: xtdHours.showAll });
    },

    get xtdHiddenEventsCount() {
        const { start, end } = getUserHourRange();
        if (!["day", "week"].includes(this.props.model.scale) || (start === 0 && end === 24)) {
            return 0;
        }
        let count = 0;
        for (const record of Object.values(this.props.model.records || {})) {
            if (record.isAllDay) {
                continue;
            }
            const startMinutes = record.start.hour * 60 + record.start.minute;
            const sameDay = record.end.hasSame(record.start, "day");
            const endMinutes = sameDay ? record.end.hour * 60 + record.end.minute : 24 * 60;
            if (startMinutes < start * 60 || endMinutes > end * 60) {
                count++;
            }
        }
        return count;
    },

    get xtdHoursNotice() {
        const { start, end } = getUserHourRange();
        const count = this.xtdHiddenEventsCount;
        if (!count) {
            return null;
        }
        if (this.xtdHoursState.showAll) {
            return {
                text: _t("Mostrando todas las horas"),
                button: _t("Volver a %(start)s:00 - %(end)s:00", { start, end }),
            };
        }
        return {
            text: count === 1
                ? _t("1 evento fuera del horario visible (%(start)s:00 - %(end)s:00)", { start, end })
                : _t("%(count)s eventos fuera del horario visible (%(start)s:00 - %(end)s:00)", { count, start, end }),
            button: _t("Mostrar todo"),
        };
    },

    toggleXtdHours() {
        xtdHours.showAll = !xtdHours.showAll;
        this.xtdHoursState.showAll = xtdHours.showAll;
        this.env.bus.trigger(HOURS_EVENT);
    },
});
