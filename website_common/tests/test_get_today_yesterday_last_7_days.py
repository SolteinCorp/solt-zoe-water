# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

"""Test cases for get_today_yesterday_last_7_days method."""

from datetime import datetime, timezone
from unittest.mock import patch

from odoo import _
from odoo.addons.website_common.controllers.portal import (
    get_today_yesterday_last_7_days,
)
from odoo.tests import TransactionCase, tagged


@tagged("get_today_yesterday_last_7_days", "portal", "website_common")
class TestGetTodayYesterdayLast7Days(TransactionCase):
    """Test cases for the get_today_yesterday_last_7_days method."""

    def test_returns_dictionary_with_three_entries(self):
        """Should return a dictionary with exactly three entries."""
        result = get_today_yesterday_last_7_days()
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 3)

        # Verify all values are tuples with 2 datetime objects
        for _key, value in result.items():
            self.assertIsInstance(value, tuple)
            self.assertEqual(len(value), 2)
            self.assertIsInstance(value[0], datetime)
            self.assertIsInstance(value[1], datetime)

    def test_contains_expected_keys(self):
        """Should contain the expected translated keys."""
        result = get_today_yesterday_last_7_days()
        self.assertIn(_("Today"), result)
        self.assertIn(_("Yesterday"), result)
        self.assertIn(_("Last 7 days"), result)

    def test_all_datetimes_are_timezone_aware(self):
        """Should return timezone-aware datetime objects in UTC."""
        result = get_today_yesterday_last_7_days()

        for key, (start, end) in result.items():
            self.assertIsNotNone(
                start.tzinfo, f"Start datetime for {key} should be timezone-aware"
            )
            self.assertIsNotNone(
                end.tzinfo, f"End datetime for {key} should be timezone-aware"
            )
            self.assertEqual(
                start.tzinfo, timezone.utc, f"Start datetime for {key} should be UTC"
            )
            self.assertEqual(
                end.tzinfo, timezone.utc, f"End datetime for {key} should be UTC"
            )

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_today_range_calculation(self, mock_datetime):
        """Should calculate today's range from 00:00:00 to 23:59:59."""
        mock_now = datetime(2025, 10, 6, 15, 30, 45, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_today_yesterday_last_7_days()
        today_start, today_end = result[_("Today")]

        # Verify start of today
        self.assertEqual(today_start.year, 2025)
        self.assertEqual(today_start.month, 10)
        self.assertEqual(today_start.day, 6)
        self.assertEqual(today_start.hour, 0)
        self.assertEqual(today_start.minute, 0)
        self.assertEqual(today_start.second, 0)
        self.assertEqual(today_start.microsecond, 0)

        # Verify end of today
        self.assertEqual(today_end.year, 2025)
        self.assertEqual(today_end.month, 10)
        self.assertEqual(today_end.day, 6)
        self.assertEqual(today_end.hour, 23)
        self.assertEqual(today_end.minute, 59)
        self.assertEqual(today_end.second, 59)
        self.assertEqual(today_end.microsecond, 0)

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_yesterday_range_calculation(self, mock_datetime):
        """Should calculate yesterday's range from 00:00:00 to 23:59:59."""
        mock_now = datetime(2025, 10, 6, 15, 30, 45, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_today_yesterday_last_7_days()
        yesterday_start, yesterday_end = result[_("Yesterday")]

        # Verify start of yesterday (Oct 5)
        self.assertEqual(yesterday_start.year, 2025)
        self.assertEqual(yesterday_start.month, 10)
        self.assertEqual(yesterday_start.day, 5)
        self.assertEqual(yesterday_start.hour, 0)
        self.assertEqual(yesterday_start.minute, 0)
        self.assertEqual(yesterday_start.second, 0)
        self.assertEqual(yesterday_start.microsecond, 0)

        # Verify end of yesterday (Oct 5)
        self.assertEqual(yesterday_end.year, 2025)
        self.assertEqual(yesterday_end.month, 10)
        self.assertEqual(yesterday_end.day, 5)
        self.assertEqual(yesterday_end.hour, 23)
        self.assertEqual(yesterday_end.minute, 59)
        self.assertEqual(yesterday_end.second, 59)
        self.assertEqual(yesterday_end.microsecond, 0)

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_last_7_days_range_calculation(self, mock_datetime):
        """Should calculate last 7 days as Monday to Sunday of previous week."""
        # Monday, Oct 6, 2025
        mock_now = datetime(2025, 10, 6, 15, 30, 45, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_today_yesterday_last_7_days()
        week_start, week_end = result[_("Last 7 days")]

        # Should start on Monday of previous week (Sep 29, 2025)
        self.assertEqual(week_start.year, 2025)
        self.assertEqual(week_start.month, 9)
        self.assertEqual(week_start.day, 29)
        self.assertEqual(week_start.hour, 0)
        self.assertEqual(week_start.minute, 0)
        self.assertEqual(week_start.second, 0)
        self.assertEqual(week_start.microsecond, 0)
        self.assertEqual(week_start.weekday(), 0)  # Monday

        # Should end on Sunday of previous week (Oct 5, 2025)
        self.assertEqual(week_end.year, 2025)
        self.assertEqual(week_end.month, 10)
        self.assertEqual(week_end.day, 5)
        self.assertEqual(week_end.hour, 23)
        self.assertEqual(week_end.minute, 59)
        self.assertEqual(week_end.second, 59)
        self.assertEqual(week_end.microsecond, 0)
        self.assertEqual(week_end.weekday(), 6)  # Sunday

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_last_7_days_from_different_weekdays(self, mock_datetime):
        """Should calculate correct previous week regardless of current weekday."""
        test_cases = [
            # (current_date, expected_monday, expected_sunday)
            (
                datetime(2025, 10, 6, 12, 0, 0, tzinfo=timezone.utc),
                (2025, 9, 29),
                (2025, 10, 5),
            ),  # Monday
            (
                datetime(2025, 10, 7, 12, 0, 0, tzinfo=timezone.utc),
                (2025, 9, 29),
                (2025, 10, 5),
            ),  # Tuesday
            (
                datetime(2025, 10, 8, 12, 0, 0, tzinfo=timezone.utc),
                (2025, 9, 29),
                (2025, 10, 5),
            ),  # Wednesday
            (
                datetime(2025, 10, 9, 12, 0, 0, tzinfo=timezone.utc),
                (2025, 9, 29),
                (2025, 10, 5),
            ),  # Thursday
            (
                datetime(2025, 10, 10, 12, 0, 0, tzinfo=timezone.utc),
                (2025, 9, 29),
                (2025, 10, 5),
            ),  # Friday
            (
                datetime(2025, 10, 11, 12, 0, 0, tzinfo=timezone.utc),
                (2025, 9, 29),
                (2025, 10, 5),
            ),  # Saturday
            (
                datetime(2025, 10, 12, 12, 0, 0, tzinfo=timezone.utc),
                (2025, 9, 29),
                (2025, 10, 5),
            ),  # Sunday
        ]

        for current_date, expected_monday, expected_sunday in test_cases:
            with self.subTest(current_date=current_date):
                mock_datetime.now.return_value = current_date
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                    *args, **kwargs
                )
                result = get_today_yesterday_last_7_days()
                week_start, week_end = result[_("Last 7 days")]

                self.assertEqual(
                    (week_start.year, week_start.month, week_start.day), expected_monday
                )
                self.assertEqual(
                    (week_end.year, week_end.month, week_end.day), expected_sunday
                )
                self.assertEqual(week_start.weekday(), 0)  # Monday
                self.assertEqual(week_end.weekday(), 6)  # Sunday

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_month_boundary_handling(self, mock_datetime):
        """Should handle month boundaries correctly."""
        # First day of October
        mock_now = datetime(2025, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_today_yesterday_last_7_days()
        yesterday_start, a_ = result[_("Yesterday")]

        # Yesterday should be last day of September
        self.assertEqual(yesterday_start.year, 2025)
        self.assertEqual(yesterday_start.month, 9)
        self.assertEqual(yesterday_start.day, 30)

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_year_boundary_handling(self, mock_datetime):
        """Should handle year boundaries correctly."""
        # First day of year
        mock_now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_today_yesterday_last_7_days()
        yesterday_start, a_ = result[_("Yesterday")]

        # Yesterday should be last day of previous year
        self.assertEqual(yesterday_start.year, 2024)
        self.assertEqual(yesterday_start.month, 12)
        self.assertEqual(yesterday_start.day, 31)

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_leap_year_february_handling(self, mock_datetime):
        """Should handle leap year February correctly."""
        # March 1 in leap year
        mock_now = datetime(2024, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_today_yesterday_last_7_days()
        yesterday_start, a_ = result[_("Yesterday")]

        # Yesterday should be February 29 (leap day)
        self.assertEqual(yesterday_start.year, 2024)
        self.assertEqual(yesterday_start.month, 2)
        self.assertEqual(yesterday_start.day, 29)

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_regular_february_handling(self, mock_datetime):
        """Should handle regular February correctly."""
        # March 1 in non-leap year
        mock_now = datetime(2025, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_today_yesterday_last_7_days()
        yesterday_start, a_ = result[_("Yesterday")]

        # Yesterday should be February 28
        self.assertEqual(yesterday_start.year, 2025)
        self.assertEqual(yesterday_start.month, 2)
        self.assertEqual(yesterday_start.day, 28)

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_last_week_across_month_boundary(self, mock_datetime):
        """Should handle last week calculation across month boundaries."""
        # Early October where previous week spans September and October
        mock_now = datetime(2025, 10, 3, 12, 0, 0, tzinfo=timezone.utc)  # Thursday
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_today_yesterday_last_7_days()
        week_start, week_end = result[_("Last 7 days")]

        # Both week should start in September 22/09/2025 - 28/09/2025
        self.assertEqual(week_start.month, 9)  # September
        self.assertEqual(week_end.month, 9)  # October

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_last_week_across_year_boundary(self, mock_datetime):
        """Should handle last week calculation across year boundaries."""
        # Early January where previous week spans December and January
        mock_now = datetime(2025, 1, 3, 12, 0, 0, tzinfo=timezone.utc)  # Friday
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_today_yesterday_last_7_days()
        week_start, week_end = result[_("Last 7 days")]

        # Previous week should start in previous year
        self.assertEqual(week_start.year, 2024)  # Previous year
        self.assertEqual(week_end.year, 2024)  # Previous year

    def test_time_precision_boundaries(self):
        """Should set precise time boundaries for all ranges."""
        result = get_today_yesterday_last_7_days()

        for key, (start, end) in result.items():
            # All start times should be exactly midnight
            self.assertEqual(start.hour, 0, f"Start hour for {key} should be 0")
            self.assertEqual(start.minute, 0, f"Start minute for {key} should be 0")
            self.assertEqual(start.second, 0, f"Start second for {key} should be 0")
            self.assertEqual(
                start.microsecond, 0, f"Start microsecond for {key} should be 0"
            )

            # All end times should be exactly 23:59:59.000000
            self.assertEqual(end.hour, 23, f"End hour for {key} should be 23")
            self.assertEqual(end.minute, 59, f"End minute for {key} should be 59")
            self.assertEqual(end.second, 59, f"End second for {key} should be 59")
            self.assertEqual(
                end.microsecond, 0, f"End microsecond for {key} should be 0"
            )

    def test_start_before_end_for_all_ranges(self):
        """Should ensure start datetime is before end datetime for all ranges."""
        result = get_today_yesterday_last_7_days()

        for key, (start, end) in result.items():
            self.assertLess(start, end, f"Start should be before end for {key}")

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_consistent_results_same_day(self, mock_datetime):
        """Should return consistent results when called multiple times in same day."""
        # Test at different times within same day
        test_times = [
            datetime(2025, 10, 6, 0, 0, 0, tzinfo=timezone.utc),  # Midnight
            datetime(2025, 10, 6, 12, 0, 0, tzinfo=timezone.utc),  # Noon
            datetime(2025, 10, 6, 23, 59, 59, tzinfo=timezone.utc),  # End of day
        ]

        results = []
        for test_time in test_times:
            mock_datetime.now.return_value = test_time
            results.append(get_today_yesterday_last_7_days())

        # All results should have identical ranges
        base_result = results[0]
        for i, other_result in enumerate(results[1:], 1):
            for key in base_result.keys():
                self.assertEqual(
                    base_result[key],
                    other_result[key],
                    f"Result {i} should match base result for key {key}",
                )

    def test_no_side_effects(self):
        """Should not modify any external state when called multiple times."""
        # Call method multiple times and verify no side effects
        results = []
        for _i in range(5):
            results.append(get_today_yesterday_last_7_days())

        # All results should have same structure
        base_keys = set(results[0].keys())
        for i, result in enumerate(results[1:], 1):
            self.assertEqual(
                set(result.keys()),
                base_keys,
                f"Result {i} should have same keys as first result",
            )

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_return_type_annotations(self, mock_datetime):
        """Should verify the return type matches the function annotation."""
        mock_now = datetime(2025, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_today_yesterday_last_7_days()

        # Should be dict[str, tuple[datetime, datetime]]
        self.assertIsInstance(result, dict)
        for key, value in result.items():
            self.assertIsInstance(key, str)
            self.assertIsInstance(value, tuple)
            self.assertEqual(len(value), 2)
            self.assertIsInstance(value[0], datetime)
            self.assertIsInstance(value[1], datetime)

    def test_7_day_range_is_exactly_7_days(self):
        """Should ensure Last 7 days range spans exactly 7 days."""
        result = get_today_yesterday_last_7_days()
        week_start, week_end = result[_("Last 7 days")]

        # Calculate the difference
        delta = week_end.date() - week_start.date()
        self.assertEqual(
            delta.days, 6, "Last 7 days should span exactly 6 days (Monday to Sunday)"
        )

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_edge_case_sunday_calculation(self, mock_datetime):
        """Should handle calculation correctly when current day is Sunday."""
        # Sunday, Oct 12, 2025
        mock_now = datetime(2025, 10, 12, 15, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_today_yesterday_last_7_days()
        week_start, week_end = result[_("Last 7 days")]

        # Previous week should be Monday Sep 30 to Sunday Oct 6
        self.assertEqual(week_start.year, 2025)
        self.assertEqual(week_start.month, 9)
        self.assertEqual(week_start.day, 29)
        self.assertEqual(week_start.weekday(), 0)  # Monday

        self.assertEqual(week_end.year, 2025)
        self.assertEqual(week_end.month, 10)
        self.assertEqual(week_end.day, 5)
        self.assertEqual(week_end.weekday(), 6)  # Sunday
