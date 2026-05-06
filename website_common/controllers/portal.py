# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

"""Common portal controller for website module."""

import logging
import re
import unicodedata
from calendar import monthrange
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from babel import Locale
from babel.core import UnknownLocaleError
from babel.dates import format_date
from odoo import _, http, models
from odoo.addons.website_common.utils.arch import FilterBarParser, SearchViewParser
from odoo.api import Environment
from odoo.exceptions import AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


def get_month_name_babel(date_obj: datetime, lang_code: str) -> str:
    """Get the localized month name for a given datetime object using Babel.

    This function handles Odoo language format codes like 'es_MX, es_AR', 'es', 'es_ES', etc.

    Args:
        date_obj (datetime): The datetime object to extract the month from.
        lang_code (str): The language code in Odoo format (e.g., 'es_MX', 'es', 'es_ES', 'en_US', 'fr_FR').

    Returns:
        str: The localized month name.

    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2024, 3, 15)
        >>> get_month_name_babel(dt, 'es')      # 'marzo'
        >>> get_month_name_babel(dt, 'es_MX')   # 'marzo'
        >>> get_month_name_babel(dt, 'es_ES')   # 'marzo'
        >>> get_month_name_babel(dt, 'en')      # 'March'
        >>> get_month_name_babel(dt, 'en_US')   # 'March'
        >>> get_month_name_babel(dt, 'fr')      # 'mars'
        >>> get_month_name_babel(dt, 'fr_FR')   # 'mars'
    """
    try:
        # Handle Odoo language codes
        if "_" in lang_code:
            # Try with the full locale first (e.g., 'es_MX')
            try:
                locale = Locale.parse(lang_code)
                return format_date(date_obj, "MMMM", locale=locale)
            except (UnknownLocaleError, ValueError):
                # If full locale fails, try with just the language part (e.g., 'es' from 'es_MX')
                lang_only = lang_code.split("_")[0]
                locale = Locale(lang_only)
                return format_date(date_obj, "MMMM", locale=locale)
        else:
            # Simple language code (e.g., 'es', 'en', 'fr')
            locale = Locale(lang_code)
            return format_date(date_obj, "MMMM", locale=locale)
    except (UnknownLocaleError, ValueError):
        # Fallback to English if locale is not supported
        try:
            return format_date(date_obj, "MMMM", locale=Locale("en"))
        except Exception:
            # Last resort fallback
            month_names_en = [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ]
            return month_names_en[date_obj.month - 1]


def get_all_month_names_babel(lang_code: str) -> list[str]:
    """Get all 12 month names for a specific locale using Babel.

    Args:
        lang_code (str): The language code in Odoo format (e.g., 'es_MX', 'es', 'es_ES').

    Returns:
        list[str]: List of 12 month names in the specified locale.

    Examples:
        >>> get_all_month_names_babel('es')
        ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
         'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        >>> get_all_month_names_babel('en_US')
        ['January', 'February', 'March', 'April', 'May', 'June',
         'July', 'August', 'September', 'October', 'November', 'December']
    """
    month_names = []
    for month in range(1, 13):
        dummy_date = datetime(
            2024, month, 1, tzinfo=timezone.utc
        )  # Use 2024 as reference year
        month_name = get_month_name_babel(dummy_date, lang_code)
        month_names.append(month_name)
    return month_names


def get_quarters_date_range() -> dict[str, tuple[datetime, datetime]]:
    """Returns a dictionary mapping localized quarter names.

    Returns a dictionary mapping localized quarter names to their respective
    start and end datetime tuples for the current year in UTC.

    Returns:
        dict: {
            _('Q1'): (start_datetime, end_datetime),
            _('Q2'): (start_datetime, end_datetime),
            _('Q3'): (start_datetime, end_datetime),
            _('Q4'): (start_datetime, end_datetime)
        }
    """
    year = datetime.now(timezone.utc).year
    return {
        _("Q1"): (
            datetime(year, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            datetime(year, 3, 31, 23, 59, 59, tzinfo=timezone.utc),
        ),
        _("Q2"): (
            datetime(year, 4, 1, 0, 0, 0, tzinfo=timezone.utc),
            datetime(year, 6, 30, 23, 59, 59, tzinfo=timezone.utc),
        ),
        _("Q3"): (
            datetime(year, 7, 1, 0, 0, 0, tzinfo=timezone.utc),
            datetime(year, 9, 30, 23, 59, 59, tzinfo=timezone.utc),
        ),
        _("Q4"): (
            datetime(year, 10, 1, 0, 0, 0, tzinfo=timezone.utc),
            datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        ),
    }


def get_today_yesterday_last_7_days() -> dict[str, tuple[datetime, datetime]]:
    """Returns a dictionary with date ranges for today, yesterday, and the last 7 days.

    Returns:
        dict[str, tuple[datetime, datetime]]: Dictionary mapping localized labels to
        tuples containing the start and end datetimes (in UTC) for:
            - Today
            - Yesterday
            - Last 7 days (previous week, Monday to Sunday)
    """
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    # Calcular el inicio de la semana anterior (lunes)
    days_since_monday = now.weekday()  # 0=lunes, 6=domingo
    last_week_monday = now - timedelta(days=days_since_monday + 7)
    # Calcular el final de la semana anterior (domingo)
    last_week_sunday = last_week_monday + timedelta(days=6)
    return {
        _("Today"): (
            datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc),
            datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc),
        ),
        _("Yesterday"): (
            datetime(
                yesterday.year,
                yesterday.month,
                yesterday.day,
                0,
                0,
                0,
                tzinfo=timezone.utc,
            ),
            datetime(
                yesterday.year,
                yesterday.month,
                yesterday.day,
                23,
                59,
                59,
                tzinfo=timezone.utc,
            ),
        ),
        _("Last 7 days"): (
            datetime(
                last_week_monday.year,
                last_week_monday.month,
                last_week_monday.day,
                0,
                0,
                0,
                tzinfo=timezone.utc,
            ),
            datetime(
                last_week_sunday.year,
                last_week_sunday.month,
                last_week_sunday.day,
                23,
                59,
                59,
                tzinfo=timezone.utc,
            ),
        ),
    }


def get_n_years_date_range(
    reference_date: datetime, count: int = 1
) -> dict[str, tuple[datetime, datetime]]:
    """Returns a dictionary mapping years to their respective start and end datetime tuples in UTC.

    Args:
        reference_date (datetime): The reference date to determine the current year.
        count (int, optional): Number of previous years to include. Defaults to 1.

    Returns:
        dict: {
            "YYYY": (start_datetime, end_datetime),
            "YYYY-1": (start_datetime, end_datetime),
            ...
        }

    Example:
        >>> from datetime import datetime, timezone
        >>> get_n_years_date_range(datetime(2024, 5, 1, tzinfo=timezone.utc), 2)
        {
            '2024': (datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc), datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)),
            '2023': (datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc), datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc)),
            '2022': (datetime(2022, 1, 1, 0, 0, tzinfo=timezone.utc), datetime(2022, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
        }
    """
    count = max(count, 1)
    result = {}
    result.update(
        {
            reference_date.strftime("%Y"): (
                datetime(reference_date.year, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(reference_date.year, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            )
        }
    )
    index = 1
    while index <= count:
        previous_year = reference_date.year - index
        result.update(
            {
                str(previous_year): (
                    datetime(previous_year, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                    datetime(previous_year, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                )
            }
        )
        index += 1
    return result


def get_n_months_date_range(
    reference_date: datetime, count: int = 1, lang_code: str = "en"
) -> dict[str, tuple[datetime, datetime]]:
    """Returns a dictionary mapping localized month-year strings to their respective start and end datetime tuples in UTC.

    Args:
        reference_date (datetime): The reference date to determine the current month and year.
        count (int, optional): Number of previous months to include. Defaults to 1.
        lang_code (str, optional): Language code for month name localization. Defaults to "en".

    Returns:
        dict: {
            "MonthName YYYY": (start_datetime, end_datetime),
            ...
        }

    Examples:
        >>> from datetime import datetime, timezone
        >>> get_n_months_date_range(datetime(2024, 5, 15, tzinfo=timezone.utc), 2, "es")
        {
            'mayo 2024': (datetime(2024, 5, 1, tzinfo=timezone.utc), datetime(2024, 5, 31, 23, 59, 59, tzinfo=timezone.utc)),
            'abril 2024': (datetime(2024, 4, 1, tzinfo=timezone.utc), datetime(2024, 4, 30, 23, 59, 59, tzinfo=timezone.utc)),
            'marzo 2024': (datetime(2024, 3, 1, tzinfo=timezone.utc), datetime(2024, 3, 31, 23, 59, 59, tzinfo=timezone.utc))
        }
        >>> get_n_months_date_range(datetime(2024, 1, 10, tzinfo=timezone.utc), 1, "en")
        {
            'January 2024': (datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 1, 31, 23, 59, 59, tzinfo=timezone.utc)),
            'December 2023': (datetime(2023, 12, 1, tzinfo=timezone.utc), datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
        }
    """
    count = max(count, 1)
    result = {}
    year, month = reference_date.year, reference_date.month

    for _i in range(count + 1):
        month_start = datetime(year, month, 1, tzinfo=timezone.utc)
        month_end = datetime(
            year, month, monthrange(year, month)[1], 23, 59, 59, tzinfo=timezone.utc
        )
        month_name = get_month_name_babel(month_start, lang_code)
        result[f"{month_name} {year}"] = (month_start, month_end)
        month -= 1
        if month < 1:
            month = 12
            year -= 1

    return result


class CommonPortalController(http.Controller):
    """Common portal controller for website module."""

    @staticmethod
    def add_many_x_field_searchbar_filters(
        model: models.Model,
        field_name: str,
        limit: int = 5,
        order_by: str = "id desc",
        sequence: int = 1,
        env: Environment | None = None,
        title: str | None = None,
        domain: list | None = None,
    ) -> dict[str, dict]:
        """Generates searchbar filters for fields of type many2one, many2many, one2many, or selection.

        Args:
            model (models.Model): The Odoo model containing the field.
            field_name (str): The name of the field to generate filters for.
            limit (int, optional): Maximum number of records to fetch for filter options. Defaults to 5.
            order_by (str, optional): Ordering for record search. Defaults to "id desc".
            sequence (int, optional): Starting sequence for filter ordering. Defaults to 1.
            env (Environment | None, optional): Odoo environment. Defaults to None.
            title (str | None, optional): Title for the field header. Defaults to None.
            domain (list | None, optional): Additional domain to filter records. Defaults to None.

        Returns:
            dict[str, dict]: Dictionary of searchbar filter definitions for the field.

        Example:
            >>> CommonPortalController.add_many_x_field_searchbar_filters(model, "partner_id")
            {
                "partner_id_divider": {...},
                "partner_id_header": {...},
                "partner_id_header": {
                    "items": {
                        "partner_id_1": {...},
                        "partner_id_2": {...},
                        ...
                    }
                }
            }
        """
        searchbar_filters = {}
        if field_name in model._fields:
            field = model._fields[field_name]
            env = env or request.env
            if field.type in ("many2one", "many2many", "one2many", "selection"):
                if field.type == "selection":
                    records = [
                        {"id": key, "display_name": value}
                        for key, value in field.selection
                    ]
                else:
                    try:
                        domain = domain or []
                        records = (
                            field.comodel_name
                            and env[field.comodel_name].search_read(
                                domain,
                                fields=["id", "display_name"],
                                limit=limit,
                                order=order_by,
                            )
                        ) or []
                    except (AccessError, Exception) as exc:
                        _logger.exception(
                            _(
                                "Error obtaining records to build filters list for field '%s': %s"
                            ),
                            field_name,
                            exc,
                            exc_info=True,
                        )
                        records = []
                if records:
                    searchbar_filters[f"{field_name}_divider"] = {
                        "label": _(f"{field.string} Start"),
                        "domain": [],
                        "sequence": sequence + 1,
                        "type": "divider",
                    }
                    searchbar_filters[f"{field_name}_header"] = {
                        "label": field.string if title is None else title,
                        "domain": [],
                        "sequence": sequence + 2,
                        "type": "header",
                        "items": {},
                    }
                    sequence += 3
                    for record in records:
                        searchbar_filters[f"{field_name}_{record['id']!s}"] = {
                            "label": _(record["display_name"]),
                            "domain": [(field_name, "in", [record["id"]])],
                            "sequence": sequence,
                            "parent": f"{field_name}_header",
                        }
                        sequence += 1
        return searchbar_filters

    @staticmethod
    def add_date_searchbar_filters(
        field_name: str, field_title: str, sequence: int = 1, lang_code: str = "en"
    ) -> dict[str, dict]:
        """Add date-based searchbar filters for Odoo portal views.

        This method generates a dictionary of searchbar filters for a given field,
        including month, quarter, and year ranges, with localized labels.

        Args:
            field_name (str): The name of the field to filter on.
            field_title (str): The title to display for the field header.
            sequence (int, optional): The starting sequence for filter ordering. Defaults to 1.
            lang_code (str, optional): Language code for month name localization. Defaults to "en".

        Returns:
            dict[str, dict]: Dictionary of searchbar filter definitions.

        Examples:
            >>> CommonPortalController.add_date_searchbar_filters("date_field", "Date")
            {
                'date_field_divider': {'label': 'Date Start', 'domain': [], 'sequence': 2, 'type': 'divider'},
                'date_field_header': {'label': 'Date', 'domain': [], 'sequence': 3, 'type': 'header'},
                'May 2024': {'label': 'May 2024', 'domain': [('date_field', '>=', datetime(2024, 5, 1, tzinfo=timezone.utc)), ('date_field', '<=', datetime(2024, 5, 31, 23, 59, 59, tzinfo=timezone.utc))], 'sequence': 4},
                'Q1': {'label': 'Q1', 'domain': [('date_field', '>=', datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)), ('date_field', '<=', datetime(2024, 3, 31, 23, 59, 59, tzinfo=timezone.utc))], 'sequence': ...},
                '2024': {'label': '2024', 'domain': [('date_field', '>=', datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)), ('date_field', '<=', datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc))], 'sequence': ...},
                ...
            }
        """
        searchbar_filters = {
            f"{field_name}_divider": {
                "label": _("Date Start"),
                "domain": [],
                "sequence": sequence + 1,
                "type": "divider",
            },
            f"{field_name}_header": {
                "label": field_title,
                "domain": [],
                "sequence": sequence + 2,
                "type": "header",
            },
        }
        sequence += 3
        now = datetime.now(timezone.utc)

        def add_filters(
            source: dict,
            key_func: Callable = lambda x: x,
            label_func: Callable = lambda x: x,
        ) -> None:
            """Adds filter definitions to the searchbar_filters dictionary.

            Args:
                source (dict): Dictionary mapping filter names to date ranges.
                key_func (Callable, optional): Function to transform filter names into keys. Defaults to identity.
                label_func (Callable, optional): Function to transform filter names into labels. Defaults to identity.

            Side Effects:
                Modifies the searchbar_filters dictionary in the enclosing scope.
                Increments the sequence variable for each filter added.
            """
            nonlocal sequence
            for name, range_ in source.items():
                searchbar_filters[f"{field_name}_{key_func(name)}"] = {
                    "label": label_func(name),
                    "domain": [
                        (field_name, ">=", range_[0]),
                        (field_name, "<=", range_[1]),
                    ],
                    "sequence": sequence,
                    "parent": f"{field_name}_header",
                }
                sequence += 1

        add_filters(
            get_today_yesterday_last_7_days(),
            key_func=lambda name: re.sub(
                r"[-\s]+",
                "_",
                re.sub(
                    r"[^\w\s-]",
                    "",
                    unicodedata.normalize("NFKD", name)
                    .encode("ascii", "ignore")
                    .decode("ascii")
                    .lower(),
                ),
            ).strip("_"),
        )
        add_filters(
            get_n_months_date_range(now, 2, lang_code=lang_code),
            lambda name: re.sub(
                r"[-\s]+",
                "_",
                re.sub(
                    r"[^\w\s-]",
                    "",
                    unicodedata.normalize("NFKD", name)
                    .encode("ascii", "ignore")
                    .decode("ascii")
                    .lower(),
                ),
            ).strip("_"),
        )
        add_filters(get_quarters_date_range(), str)
        add_filters(get_n_years_date_range(now, 2), lambda name: _(str(name)))

        return searchbar_filters

    @staticmethod
    def extract_search_filter_group_by_from_search_view(
        model_name: str, env: Environment | None = None, **kwargs
    ) -> dict:
        """
        Extracts search, filter, and group-by definitions from the search view architecture of a given Odoo model.

        Args:
            model_name (str): The name of the Odoo model to extract search view definitions from.
            env (Environment | None, optional): The Odoo environment. Defaults to None, which uses the current request environment.
            **kwargs: Additional keyword arguments passed to the SearchViewParser's parse method.

        Returns:
            dict: Parsed search, filter, and group-by definitions from the model's search view.
                  Returns an empty dictionary if the model does not exist or an error occurs.
        """
        # initialize result
        result = {}
        # assign env
        env = env or request.env

        def model_exists() -> bool:
            """
            Check if the given model exists in the Odoo environment.

            Returns:
                bool: True if the model exists and its _fields attribute is a dict, False otherwise.
            """
            try:
                var = env[model_name]._fields
                return isinstance(var, dict)
            except Exception:
                return False

        # check if model exists
        if not model_exists():
            _logger.error(
                _(f"The model {model_name} does not exist in this Odoo environment.")
            )
            return result

        try:
            # obtain search view architecture
            views_result = env[model_name].get_views([[False, "search"]])
            # create parser and parse
            psr = SearchViewParser(views_result["views"]["search"]["arch"])
            result = psr.parse(**kwargs)
        except Exception:
            _logger.exception(_(f"Error parsing search views for model {model_name}"))

        return result

    @staticmethod
    def extract_search_view_to_searchbar(
        model_name: str, env: Environment | None = None, **kwargs
    ) -> dict:
        """Extract search view components and parse them into searchbar configuration."""
        searchbar_parser = FilterBarParser(
            arch=CommonPortalController.extract_search_filter_group_by_from_search_view(
                model_name=model_name, env=env, **kwargs
            ),
            model_name=model_name,
            env=env,
        )
        return searchbar_parser.parse(**kwargs)
