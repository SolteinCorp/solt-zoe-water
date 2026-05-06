# -*- coding: utf-8 -*-
# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
from datetime import datetime

from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.tools import format_datetime


class RemainingDaysConverter(models.AbstractModel):
    _name = "ir.qweb.field.remaining_days"
    _description = "Qweb Field Remaining Days"
    _inherit = "ir.qweb.field"

    @api.model
    def get_available_options(self) -> dict:
        """Return available QWeb field options, adding a 'format' string option for datetime formatting.

        Returns:
            dict: Merged options including 'format' with type 'string' and label 'Datetime format'.
        """
        options = super().get_available_options()
        options.update(format={"type": "string", "string": _("Datetime format")})
        return options

    def diff_days(self, value: datetime) -> int:
        """Compute the day difference between the given date and now.

        Args:
            value (datetime): Target datetime; time components are zeroed to compare whole days.

        Returns:
            int: Number of days from now to 'value'. Negative for past dates, positive for future dates.

        Note:
            Comparison uses 'fields.Datetime.now()' and ignores time-of-day by setting time to 00:00:00.
        """
        value = value.replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            value
            - fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).days

    def formatted_value(self, value: datetime, options: dict) -> str:
        """Format a 'datetime' using Odoo's 'format_datetime'.

        Args:
            value (datetime): The 'datetime' to format.
            options (dict): Options dict that may contain 'format' for a custom pattern.

        Returns:
            str: The formatted 'datetime' string.
        """
        return format_datetime(self.env, value, dt_format=options.get("format"))

    def diff_string(self, value: datetime, options: dict) -> str:
        """Return a human-readable description of the day difference.

        Args:
            value (datetime): Target 'datetime' to compare against 'now'.
            options (dict): Options dict used for fallback formatting when range is large.

        Returns:
            str: One of 'Yesterday', 'Today', 'Tomorrow', relative day text, or a formatted date.
        """
        diff = self.diff_days(value)
        if not diff:
            return ""
        if diff == -1:
            return _("Yesterday")
        elif diff == 0:
            return _("Today")
        elif diff == 1:
            return _("Tomorrow")
        if abs(diff) > 99:
            return self.formatted_value(value, options)
        if diff < 0:
            return _("%s days ago") % abs(diff)
        return _("In %s days") % diff

    def diff_class(self, value: datetime) -> str:
        """Return a Bootstrap text class based on day difference.

        Args:
            value (datetime): Target 'datetime'.

        Returns:
            str: 'text-danger' for past, 'text-warning' for today, 'text-success' for future.
        """
        diff = self.diff_days(value)
        if diff < 0:
            return "text-danger"
        elif diff == 0:
            return "text-warning"
        else:
            return "text-success"

    @api.model
    def value_to_html(self, value, options) -> str:
        """Render the relative day description wrapped in a styled '<small>' tag.

        Args:
            value (datetime): Target 'datetime'.
            options (dict): Options dict forwarded to 'diff_string'.

        Returns:
            str: Safe HTML markup with styling and human-readable diff text.
        """
        return Markup(
            '<small class="fw-bold %s">%s</small>'
            % (self.diff_class(value), self.diff_string(value, options))
        )
