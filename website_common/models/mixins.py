# -*- coding: utf-8 -*-
# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
from datetime import date, datetime, time
from typing import Any

from dateutil import rrule as rr
from odoo import _, api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError
from pytz import timezone

RRULE_TYPE_RECURRENCE = [
    ("always", "Always"),
    ("one_time", "One Time"),
    ("recurrent", "Recurrent"),
]

RRULE_TYPE_SELECTION = [
    ("weekly", "Weeks"),
    ("monthly", "Months"),
    ("yearly", "Years"),
]

END_TYPE_SELECTION = [
    ("count", "Number of repetitions"),
    ("end_date", "End date"),
    ("forever", "Forever"),
]


def float_to_time(number: float) -> time:
    """
    Convierte un número flotante que representa horas decimales en un objeto time.

    :param number: Número flotante que representa la hora (por ejemplo, 13.5 para 13:30).
    :type number: float
    :return: Objeto time correspondiente a la hora y minutos.
    :rtype: time
    """
    hours, remainder = divmod(number, 1)
    minutes = int(remainder * 60)
    return time(int(hours), minutes)


def is_leap(year: int) -> bool:
    """
    Determina si un año es bisiesto.

    Un año es bisiesto si es divisible por 4, excepto los años que son divisibles por 100,
    a menos que también sean divisibles por 400.

    :param year: Año a evaluar.
    :type year: int
    :return: True si el año es bisiesto, False en caso contrario.
    :rtype: bool
    """
    if year % 4 == 0:
        if year % 100 == 0:
            if year % 400 == 0:
                return True
            return False
        return True
    return False


def locate_date_on_current_year(dt: datetime | date | None, default: Any = None):
    """
    Localiza una fecha dada en el año actual, manteniendo el mes y el día originales.

    Si la fecha es 29 de febrero y el año actual no es bisiesto, ajusta el día a 28.
    Si `dt` es None, retorna el valor por defecto proporcionado.

    :param dt: Fecha a ajustar al año actual (puede ser datetime, date o None).
    :type dt: datetime | date | None
    :param default: Valor a retornar si `dt` es None.
    :type default: Any
    :return: Fecha ajustada al año actual, o el valor por defecto si `dt` es None.
    :rtype: datetime | date | Any
    """
    if dt is None:
        return default
    year = fields.Datetime.today().year
    if dt.month == 2 and dt.day == 29 and not is_leap(year):
        return dt.replace(year=year, day=28)
    try:
        return dt.replace(year=year)
    except (ValueError, Exception):
        return dt


class ModelRecursiveMixin(models.AbstractModel):
    _name = "model.recursive.mixin"
    _description = "Recursive Model Mixin"

    recurrence_type = fields.Selection(
        RRULE_TYPE_RECURRENCE,
        string="Recurrence",
        default="always",
        help="Tipo de recurrencia: Siempre, Una vez, o Recurrente.",
    )
    frequency = fields.Selection(
        RRULE_TYPE_SELECTION,
        string="Frequency",
        default="yearly",
        help="Frecuencia de la recurrencia: Semanal, Mensual o Anual.",
    )
    end_type = fields.Selection(
        END_TYPE_SELECTION,
        string="End Type",
        default="forever",
        help="Tipo de finalización: Número de repeticiones, Fecha de fin, o Para siempre.",
    )
    interval = fields.Integer(
        "Interval",
        default=1,
        help="Intervalo entre recurrencias. Por ejemplo, cada 2 semanas.",
    )
    by_week_day = fields.Char(
        "Week days",
        help="Días de la semana en los que ocurre la recurrencia (ej: MO,WE,FR).",
    )
    by_month = fields.Char(
        "Months", help="Meses del año en los que ocurre la recurrencia (ej: 1,6,12)."
    )
    by_month_day = fields.Char(
        "Month days",
        help="Días del mes en los que ocurre la recurrencia (ej: 1,15,30).",
    )
    dt_start = fields.Date("Start Date", help="Fecha de inicio de la recurrencia.")
    dt_end = fields.Date("End Date", help="Fecha de finalización de la recurrencia.")
    count = fields.Integer(
        "Count", default=0, help="Número de veces que se repite la recurrencia."
    )
    until = fields.Date("Until", help="Fecha hasta la cual se repite la recurrencia.")
    tm_start = fields.Float(
        "Start Time",
        default=0,
        digits=(2, 2),
        help="Hora de inicio en formato decimal (ej: 13.5 = 13:30).",
    )
    tm_end = fields.Float(
        "End Time",
        default=23.99,
        digits=(2, 2),
        help="Hora de finalización en formato decimal (ej: 18.75 = 18:45).",
    )
    recursive_rule_string = fields.Char(
        "Recursive Rule",
        compute="_compute_recursive_rule_string",
        help="Cadena RRULE calculada automáticamente según los parámetros de recurrencia.",
    )
    tz = fields.Selection(
        _tz_get,
        string="Timezone",
        default=lambda self: self._context.get("tz"),
        help="When printing documents and exporting/importing data, time values are computed according to this timezone.\n"
        "If the timezone is not set, UTC (Coordinated Universal Time) is used.\n"
        "Anywhere else, time values are computed according to the time offset of your web client.",
    )

    @api.depends(
        "recurrence_type",
        "frequency",
        "end_type",
        "interval",
        "by_week_day",
        "by_month_day",
        "by_month",
        "count",
        "until",
    )
    def _compute_recursive_rule_string(self) -> None:
        """
        Calcula y asigna la cadena de regla recursiva (RRULE) para el registro actual.

        Esta función construye una cadena RRULE basada en los valores de los campos de recurrencia
        del registro, siguiendo el estándar iCalendar. La cadena resultante se almacena en el campo
        `recursive_rule_string`.

        Campos observados:
            - recurrence_type
            - frequency
            - end_type
            - interval
            - by_week_day
            - by_month_day
            - by_month
            - count
            - until

        :return: None
        """
        for record in self:
            rule_str = "RRULE:"
            if record.frequency:
                rule_str += "FREQ=%s;" % record.frequency.upper()
            if record.end_type == "end_date" and record.until:
                rule_str += "UNTIL=%s;" % self.join_date_time(
                    record.until, False
                ).strftime("%Y%m%dT%H%M%S")
            if record.end_type == "count":
                rule_str += "COUNT=%s;" % record.count if record.count else 1
            if record.by_week_day and record.by_week_day != "":
                rule_str += "BYDAY=%s;" % record.by_week_day
            if record.by_month and record.by_month != "":
                rule_str += "BYMONTH=%s;" % record.by_month
            if record.by_month_day and record.by_month_day != "":
                rule_str += "BYMONTHDAY=%s;" % record.by_month_day
            rule_str += "INTERVAL=%s;" % record.interval if record.interval else 1
            record.recursive_rule_string = (
                rule_str[0:-1] if rule_str != "RRULE:" else ""
            )

    @api.constrains("tm_start", "tm_end")
    def _time_constraints(self) -> None:
        """
        Valida las restricciones de los campos de tiempo y fecha.

        - tm_start y tm_end no pueden ser negativos ni mayores a 23.99.
        - tm_start no puede ser mayor que tm_end.
        - dt_start no puede ser mayor o igual que dt_end.

        Lanza una ValidationError si alguna restricción no se cumple.
        """
        if self.tm_start < 0 or self.tm_end < 0:
            ValidationError(_("Time values cannot be negative."))
        if self.tm_start > 23.99 or self.tm_end > 23.99:
            ValidationError(_("Time values cannot be over 23.99."))
        if self.tm_start > self.tm_end:
            ValidationError(_("Start time cannot be over end time."))
        if self.dt_start and self.dt_end and self.dt_start >= self.dt_end:
            ValidationError(_("Start date cannot be over end date."))

    def _locate_date_on_current_year(self, dt: datetime) -> datetime:
        """
        Localiza una fecha dada en el año actual, manteniendo el mes y el día originales.

        :param dt: Fecha a ajustar al año actual.
        :type dt: datetime
        :return: Fecha con el año actualizado al año actual.
        :rtype: datetime
        """
        return dt.replace(year=fields.Datetime.today().year)

    def join_date_time(self, dt: datetime, start: bool = True) -> datetime:
        """
        Une una fecha dada con la hora de inicio o fin configurada en el registro.

        :param dt: Fecha a la que se le agregará la hora.
        :type dt: datetime
        :param start: Si es True, utiliza la hora de inicio; si es False, la hora de fin.
        :type start: bool
        :return: Objeto datetime con la fecha ajustada al año actual y la hora correspondiente.
        :rtype: datetime
        """
        self.ensure_one()
        dt = datetime.combine(
            locate_date_on_current_year(dt),
            float_to_time(self.tm_start) if start else float_to_time(self.tm_end),
        )
        return dt

    def _get_default_tz(self) -> str:
        """
        Obtiene la zona horaria predeterminada para el registro actual.

        Retorna la zona horaria configurada en el registro (`self.tz`), o la zona horaria del usuario actual,
        o, en su defecto, 'America/Mexico_City'.

        :return: Cadena con el nombre de la zona horaria.
        :rtype: str
        """
        self.ensure_one()
        return self.tz or self.env.user.tz or "America/Mexico_City"

    def _get_dt(
        self,
        dt: datetime.date,
        start: bool = True,
        utc: bool = False,
        naive: bool = False,
    ) -> datetime:
        """
        Devuelve un objeto datetime combinando una fecha dada con la hora de inicio o fin del registro.

        Si se especifica `utc`, convierte el resultado a UTC usando la zona horaria configurada.
        Si se especifica `naive`, elimina la información de zona horaria del resultado.

        :param dt: Fecha base a combinar.
        :type dt: datetime.date
        :param start: Si es True, usa la hora de inicio; si es False, la de fin.
        :type start: bool
        :param utc: Si es True, convierte el resultado a UTC.
        :type utc: bool
        :param naive: Si es True, elimina la información de zona horaria.
        :type naive: bool
        :return: Objeto datetime ajustado.
        :rtype: datetime
        """
        self.ensure_one()
        dt_start = fields.Datetime.today()
        if dt:
            dt_start = locate_date_on_current_year(dt)
        dt_start = datetime.combine(
            dt_start, float_to_time(self.tm_start if start else self.tm_end)
        )
        if utc:
            dt_start = timezone(self._get_default_tz()).localize(dt_start)
            dt_start = dt_start.astimezone(timezone("UTC"))
        if naive:
            dt_start = dt_start.replace(tzinfo=None)
        return dt_start

    def get_dt_end(self, utc: bool = False, naive: bool = False) -> datetime:
        """
        Devuelve la fecha y hora de finalización del registro, combinando la fecha `dt_end` con la hora de fin.
        Si se especifica `utc`, convierte el resultado a UTC usando la zona horaria configurada.
        Si se especifica `naive`, elimina la información de zona horaria del resultado.

        :param utc: Si es True, convierte el resultado a UTC.
        :type utc: bool
        :param naive: Si es True, elimina la información de zona horaria.
        :type naive: bool
        :return: Objeto datetime ajustado.
        :rtype: datetime
        """
        return self._get_dt(self.dt_end, False, utc=utc, naive=naive)

    def get_dt_start(self, utc: bool = False, naive: bool = False) -> datetime:
        """
        Devuelve la fecha y hora de inicio del registro, combinando la fecha `dt_start` con la hora de inicio.
        Si se especifica `utc`, convierte el resultado a UTC usando la zona horaria configurada.
        Si se especifica `naive`, elimina la información de zona horaria del resultado.

        :param utc: Si es True, convierte el resultado a UTC.
        :type utc: bool
        :param naive: Si es True, elimina la información de zona horaria.
        :type naive: bool
        :return: Objeto datetime ajustado.
        :rtype: datetime
        """
        return self._get_dt(self.dt_start, utc=utc, naive=naive)

    def next_recursions(self, quantity: int = 1) -> list | bool:
        """
        Calcula las próximas fechas de recurrencia según la regla RRULE configurada en el registro.

        :param quantity: Número de ocurrencias siguientes a calcular.
        :type quantity: int
        :return: Lista de fechas de recurrencia o False si no hay regla definida.
        :rtype: list | bool
        """
        self.ensure_one()
        if self.recursive_rule_string == "":
            return False
        rule = rr.rrulestr(self.recursive_rule_string)
        return list(rule.xafter(count=quantity, inc=True, dt=self.get_dt_start()))
