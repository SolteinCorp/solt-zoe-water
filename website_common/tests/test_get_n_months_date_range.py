# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

"""Tests for the get_n_months_date_range method."""

from datetime import datetime, timezone
from unittest.mock import patch

from odoo.addons.website_common.controllers.portal import (
    get_n_months_date_range,
)
from odoo.tests.common import TransactionCase, tagged


@tagged("get_n_months_date_range", "portal", "website_common")
class TestGetNMonthsDateRange(TransactionCase):
    """Test cases for get_n_months_date_range function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.maxDiff = None

        # Reference dates for various scenarios
        self.ref_date_oct_2025 = datetime(
            2025, 10, 15, tzinfo=timezone.utc
        )  # Current month
        self.ref_date_jan_2025 = datetime(
            2025, 1, 15, tzinfo=timezone.utc
        )  # Start of year
        self.ref_date_dec_2025 = datetime(
            2025, 12, 31, tzinfo=timezone.utc
        )  # End of year
        self.ref_date_feb_2024 = datetime(
            2024, 2, 29, tzinfo=timezone.utc
        )  # Leap year February
        self.ref_date_feb_2025 = datetime(
            2025, 2, 15, tzinfo=timezone.utc
        )  # Non-leap year February

    # --- Basic functionality tests ---

    def test_default_parameters(self):
        """Test get_n_months_date_range with default parameters."""
        result = get_n_months_date_range(self.ref_date_oct_2025)

        # Should return 2 months (current + 1 previous)
        self.assertEqual(len(result), 2)

        # Check month names are in English by default with years
        month_names = list(result.keys())
        self.assertEqual(set(month_names), {"October 2025", "September 2025"})

        # Verify date ranges for October 2025
        oct_range = result["October 2025"]
        self.assertEqual(
            oct_range[0], datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(
            oct_range[1], datetime(2025, 10, 31, 23, 59, 59, tzinfo=timezone.utc)
        )

        # Verify date ranges for September 2025
        sep_range = result["September 2025"]
        self.assertEqual(
            sep_range[0], datetime(2025, 9, 1, 0, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(
            sep_range[1], datetime(2025, 9, 30, 23, 59, 59, tzinfo=timezone.utc)
        )

    def test_explicit_count_parameter(self):
        """Test get_n_months_date_range with explicit count parameter."""
        result = get_n_months_date_range(self.ref_date_oct_2025, count=3)

        # Should return 4 months (current + 3 previous)
        self.assertEqual(len(result), 4)

        # Check expected months with years
        expected_months = {"October 2025", "September 2025", "August 2025", "July 2025"}
        self.assertEqual(set(result.keys()), expected_months)

    def test_language_parameter(self):
        """Test get_n_months_date_range with different language parameters."""
        # Spanish
        result_es = get_n_months_date_range(
            self.ref_date_oct_2025, count=1, lang_code="es"
        )
        self.assertEqual(len(result_es), 2)
        self.assertEqual(set(result_es.keys()), {"octubre 2025", "septiembre 2025"})

        # French
        result_fr = get_n_months_date_range(
            self.ref_date_oct_2025, count=1, lang_code="fr"
        )
        self.assertEqual(len(result_fr), 2)
        self.assertEqual(set(result_fr.keys()), {"octobre 2025", "septembre 2025"})

        # German
        result_de = get_n_months_date_range(
            self.ref_date_oct_2025, count=1, lang_code="de"
        )
        self.assertEqual(len(result_de), 2)
        self.assertEqual(set(result_de.keys()), {"Oktober 2025", "September 2025"})

    # --- Edge cases and boundary tests ---

    def test_year_transition(self):
        """Test get_n_months_date_range when months span across years."""
        # January 2025 going back 2 months should cross into 2024
        result = get_n_months_date_range(self.ref_date_jan_2025, count=2)

        # Should return 3 months (Jan 2025, Dec 2024, Nov 2024)
        self.assertEqual(len(result), 3)
        self.assertEqual(
            set(result.keys()), {"January 2025", "December 2024", "November 2024"}
        )

        # Check December is from 2024
        dec_range = result["December 2024"]
        self.assertEqual(dec_range[0].year, 2024)
        self.assertEqual(
            dec_range[0], datetime(2024, 12, 1, 0, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(
            dec_range[1], datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        )

    def test_multi_year_span(self):
        """Test get_n_months_date_range when months span multiple years."""
        # October 2025 going back 14 months crosses into 2024
        result = get_n_months_date_range(self.ref_date_oct_2025, count=14)

        # Should return 15 months (Oct 2025 back to Aug 2024)
        self.assertEqual(len(result), 15)

        # Check August 2024 is included and correctly formed
        self.assertIn("August 2024", result)
        aug_2024_range = result["August 2024"]
        self.assertEqual(
            aug_2024_range[0], datetime(2024, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(
            aug_2024_range[1], datetime(2024, 8, 31, 23, 59, 59, tzinfo=timezone.utc)
        )

    def test_count_zero_or_negative(self):
        """Test get_n_months_date_range with zero or negative count."""
        # Count = 0 should be treated as count = 1
        result_zero = get_n_months_date_range(self.ref_date_oct_2025, count=0)
        self.assertEqual(len(result_zero), 2)  # Current + 1 previous
        self.assertEqual(set(result_zero.keys()), {"October 2025", "September 2025"})

        # Negative count should also be treated as count = 1
        result_negative = get_n_months_date_range(self.ref_date_oct_2025, count=-5)
        self.assertEqual(len(result_negative), 2)  # Current + 1 previous
        self.assertEqual(
            set(result_negative.keys()), {"October 2025", "September 2025"}
        )

    def test_large_count(self):
        """Test get_n_months_date_range with large count value."""
        # Large count (3 years worth of months = 36 months)
        result = get_n_months_date_range(self.ref_date_oct_2025, count=35)

        # Should return 36 months (Oct 2025 back to Nov 2022)
        self.assertEqual(len(result), 36)

        # Check the oldest month is November 2022
        self.assertIn("November 2022", result)
        nov_2022_range = result["November 2022"]
        self.assertEqual(nov_2022_range[0].year, 2022)
        self.assertEqual(nov_2022_range[0].month, 11)

    def test_leap_year_february(self):
        """Test get_n_months_date_range with February in a leap year."""
        # March 2024 going back 1 month to February 2024 (leap year)
        march_2024 = datetime(2024, 3, 15, tzinfo=timezone.utc)
        result = get_n_months_date_range(march_2024, count=1)

        # Check February 2024 is included
        self.assertIn("February 2024", result)
        feb_range = result["February 2024"]
        self.assertEqual(feb_range[1].day, 29)  # February 2024 has 29 days

    def test_non_leap_year_february(self):
        """Test get_n_months_date_range with February in a non-leap year."""
        # March 2025 going back 1 month to February 2025 (non-leap year)
        march_2025 = datetime(2025, 3, 15, tzinfo=timezone.utc)
        result = get_n_months_date_range(march_2025, count=1)

        # Check February 2025 is included
        self.assertIn("February 2025", result)
        feb_range = result["February 2025"]
        self.assertEqual(feb_range[1].day, 28)  # February 2025 has 28 days

    def test_months_with_different_days(self):
        """Test get_n_months_date_range with various months having different days."""
        result = get_n_months_date_range(self.ref_date_oct_2025, count=11)  # Full year

        # Expected days in each month (for 2025-2024)
        expected_days = {
            1: 31,  # January
            2: 28,  # February 2025 (non-leap)
            3: 31,  # March
            4: 30,  # April
            5: 31,  # May
            6: 30,  # June
            7: 31,  # July
            8: 31,  # August
            9: 30,  # September
            10: 31,  # October
            11: 30,  # November
            12: 31,  # December
        }

        # Verify each month has correct number of days
        for start_date, end_date in result.values():
            month_num = start_date.month
            expected_last_day = expected_days[month_num]
            self.assertEqual(end_date.day, expected_last_day)

    # --- Error cases and validations ---

    def test_invalid_inputs(self):
        """Test get_n_months_date_range with invalid inputs."""
        # None reference date
        with self.assertRaises(AttributeError):
            get_n_months_date_range(None, count=1)

        # Invalid reference date type
        with self.assertRaises(AttributeError):
            get_n_months_date_range("not a date", count=1)

        # Invalid count type
        with self.assertRaises(TypeError):
            get_n_months_date_range(self.ref_date_oct_2025, count="invalid")

    def test_invalid_language(self):
        """Test get_n_months_date_range with invalid language."""
        # Invalid language should fallback to English
        result = get_n_months_date_range(
            self.ref_date_oct_2025, count=1, lang_code="xx_XX"
        )

        # Should still return months in English with years
        self.assertEqual(len(result), 2)
        month_names = list(result.keys())
        self.assertEqual(set(month_names), {"October 2025", "September 2025"})

    # --- Data format and structure tests ---

    def test_datetime_precision(self):
        """Test precision of returned datetime objects."""
        result = get_n_months_date_range(self.ref_date_oct_2025, count=1)

        for start_date, end_date in result.values():
            # Start dates should be at midnight (00:00:00.000000)
            self.assertEqual(start_date.hour, 0)
            self.assertEqual(start_date.minute, 0)
            self.assertEqual(start_date.second, 0)
            self.assertEqual(start_date.microsecond, 0)

            # End dates should be at 23:59:59.000000
            self.assertEqual(end_date.hour, 23)
            self.assertEqual(end_date.minute, 59)
            self.assertEqual(end_date.second, 59)
            self.assertEqual(end_date.microsecond, 0)

    def test_timezone_consistency(self):
        """Test timezone consistency of returned datetime objects."""
        result = get_n_months_date_range(self.ref_date_oct_2025, count=3)

        for start_date, end_date in result.values():
            # All dates should have UTC timezone
            self.assertEqual(start_date.tzinfo, timezone.utc)
            self.assertEqual(end_date.tzinfo, timezone.utc)

    def test_dict_structure(self):
        """Test structure of returned dictionary."""
        result = get_n_months_date_range(self.ref_date_oct_2025, count=2)

        # Should be a dictionary
        self.assertIsInstance(result, dict)

        # Keys should be strings (month names with years)
        keys = result.keys()
        for key in keys:
            self.assertIsInstance(key, str)
            # Should contain a year (4 digits)
            self.assertRegex(key, r"\d{4}")

        # Values should be tuples of datetime objects
        for value in result.values():
            self.assertIsInstance(value, tuple)
            self.assertEqual(len(value), 2)
            self.assertIsInstance(value[0], datetime)
            self.assertIsInstance(value[1], datetime)

    # --- Mocking tests ---

    def test_month_name_integration(self):
        """Test integration with get_month_name_babel function."""
        with patch(
            "odoo.addons.website_common.controllers.portal.get_month_name_babel"
        ) as mock_get_name:
            # Setup mock to return custom month names
            def side_effect(date_obj, _lang_code):
                """Mock function to return custom month name format."""
                return f"Month-{date_obj.month}"

            mock_get_name.side_effect = side_effect

            # Call function with our mock
            result = get_n_months_date_range(
                self.ref_date_oct_2025, count=1, lang_code="test_lang"
            )

            # Verify mock was called correctly
            self.assertEqual(mock_get_name.call_count, 2)  # Called for each month

            # Check keys have our custom format with years
            self.assertEqual(set(result.keys()), {"Month-10 2025", "Month-9 2025"})

    def test_monthrange_integration(self):
        """Test integration with calendar.monthrange function."""
        with patch(
            "odoo.addons.website_common.controllers.portal.monthrange"
        ) as mock_monthrange:
            # Setup mock to return fixed values for last day of month
            mock_monthrange.return_value = (0, 30)  # (weekday, days_in_month)

            # Call function with our mock
            result = get_n_months_date_range(self.ref_date_oct_2025, count=1)

            # Verify mock was called for both months
            self.assertEqual(mock_monthrange.call_count, 2)

            # All months should now end on the 30th day
            for _, end_date in result.values():
                self.assertEqual(end_date.day, 30)
                self.assertEqual(end_date.hour, 23)
                self.assertEqual(end_date.minute, 59)
                self.assertEqual(end_date.second, 59)

    # --- Performance test ---

    def test_performance_with_large_count(self):
        """Test performance with very large count value."""
        import time

        start_time = time.time()
        # Try with a large count (5 years = 60 months)
        result = get_n_months_date_range(self.ref_date_oct_2025, count=59)
        end_time = time.time()

        # Should complete in reasonable time (less than 1 second for 60 months)
        self.assertLess(end_time - start_time, 1.0)
        self.assertEqual(len(result), 60)

    # --- Additional tests for new format ---

    def test_month_year_format_consistency(self):
        """Test that all returned keys follow the 'Month YYYY' format."""
        result = get_n_months_date_range(self.ref_date_oct_2025, count=5)

        keys = result.keys()
        for key in keys:
            # Should match pattern "MonthName YYYY"
            parts = key.split()
            self.assertEqual(
                len(parts), 2, f"Key '{key}' should have format 'Month YYYY'"
            )

            # Second part should be a 4-digit year
            year_part = parts[1]
            self.assertTrue(
                year_part.isdigit(), f"Year part '{year_part}' should be numeric"
            )
            self.assertEqual(
                len(year_part), 4, f"Year part '{year_part}' should be 4 digits"
            )

    def test_cross_year_boundary_detailed(self):
        """Test detailed cross-year boundary behavior."""
        # Test January going back several months
        result = get_n_months_date_range(self.ref_date_jan_2025, count=3)

        # Should have months from 2025 and 2024
        expected_keys = {
            "January 2025",
            "December 2024",
            "November 2024",
            "October 2024",
        }
        self.assertEqual(set(result.keys()), expected_keys)

        # Verify dates are correct
        jan_range = result["January 2025"]
        self.assertEqual(
            jan_range[0], datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(
            jan_range[1], datetime(2025, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
        )

        dec_range = result["December 2024"]
        self.assertEqual(
            dec_range[0], datetime(2024, 12, 1, 0, 0, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(
            dec_range[1], datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        )
