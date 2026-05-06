# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

"""Tests for get_n_years_date_range function."""

from datetime import datetime, timezone

from odoo.addons.website_common.controllers.portal import get_n_years_date_range
from odoo.tests.common import TransactionCase, tagged


@tagged("get_n_years_date_range", "website_common", "portal")
class TestGetNYearsDateRange(TransactionCase):
    """Test cases for get_n_years_date_range function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.maxDiff = None
        # Standard reference dates for testing
        self.ref_date_2024 = datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc)
        self.ref_date_2025 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.ref_date_leap_year = datetime(2024, 2, 29, 10, 0, 0, tzinfo=timezone.utc)

    # ========== POSITIVE TEST CASES ==========

    def test_default_count_one_year(self):
        """Test default behavior with count=1 (default parameter)."""
        result = get_n_years_date_range(self.ref_date_2024)

        expected = {
            "2024": (
                datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "2023": (
                datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
        }

        self.assertEqual(result, expected)
        self.assertEqual(len(result), 2)  # Current year + 1 previous year

    def test_explicit_count_one_year(self):
        """Test explicit count=1."""
        result = get_n_years_date_range(self.ref_date_2024, count=1)

        expected = {
            "2024": (
                datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "2023": (
                datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
        }

        self.assertEqual(result, expected)

    def test_count_two_years(self):
        """Test with count=2."""
        result = get_n_years_date_range(self.ref_date_2024, count=2)

        expected = {
            "2024": (
                datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "2023": (
                datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "2022": (
                datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2022, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
        }

        self.assertEqual(result, expected)
        self.assertEqual(len(result), 3)  # Current year + 2 previous years

    def test_count_five_years(self):
        """Test with count=5."""
        result = get_n_years_date_range(self.ref_date_2024, count=5)

        expected_years = ["2024", "2023", "2022", "2021", "2020", "2019"]

        self.assertEqual(len(result), 6)  # Current year + 5 previous years
        self.assertEqual(set(result.keys()), set(expected_years))

        # Verify each year has correct date range
        for year_str in expected_years:
            year_int = int(year_str)
            expected_start = datetime(year_int, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            expected_end = datetime(year_int, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

            self.assertEqual(result[year_str], (expected_start, expected_end))

    def test_count_ten_years(self):
        """Test with count=10."""
        result = get_n_years_date_range(self.ref_date_2024, count=10)

        expected_years = [str(year) for year in range(2024, 2013, -1)]  # 2024 to 2014

        self.assertEqual(len(result), 11)  # Current year + 10 previous years
        self.assertEqual(set(result.keys()), set(expected_years))

    # ========== EDGE CASES ==========

    def test_count_zero(self):
        """Test with count=0 (should be treated as count=1 due to max(count, 1))."""
        result = get_n_years_date_range(self.ref_date_2024, count=0)

        expected = {
            "2024": (
                datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "2023": (
                datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
        }

        self.assertEqual(result, expected)
        self.assertEqual(len(result), 2)

    def test_count_negative(self):
        """Test with negative count (should be treated as count=1 due to max(count, 1))."""
        result = get_n_years_date_range(self.ref_date_2024, count=-5)

        expected = {
            "2024": (
                datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "2023": (
                datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
        }

        self.assertEqual(result, expected)
        self.assertEqual(len(result), 2)

    def test_large_count(self):
        """Test with large count value."""
        result = get_n_years_date_range(self.ref_date_2024, count=50)

        expected_years = [str(year) for year in range(2024, 1973, -1)]  # 2024 to 1974

        self.assertEqual(len(result), 51)  # Current year + 50 previous years
        self.assertEqual(set(result.keys()), set(expected_years))

        # Verify first and last years
        self.assertIn("2024", result)
        self.assertIn("1974", result)

    # ========== LEAP YEAR CASES ==========

    def test_leap_year_reference_date(self):
        """Test with reference date in leap year."""
        result = get_n_years_date_range(self.ref_date_leap_year, count=1)

        expected = {
            "2024": (
                datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "2023": (
                datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
        }

        self.assertEqual(result, expected)

        # Verify leap year handling doesn't affect year boundaries
        leap_year_range = result["2024"]
        self.assertEqual(leap_year_range[0].month, 1)
        self.assertEqual(leap_year_range[0].day, 1)
        self.assertEqual(leap_year_range[1].month, 12)
        self.assertEqual(leap_year_range[1].day, 31)

    def test_spanning_multiple_leap_years(self):
        """Test spanning multiple leap years."""
        ref_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        result = get_n_years_date_range(ref_date, count=8)  # 2024 back to 2016

        leap_years_in_range = ["2024", "2020", "2016"]

        for leap_year in leap_years_in_range:
            self.assertIn(leap_year, result)
            # Verify leap years still have standard year boundaries
            year_range = result[leap_year]
            self.assertEqual(
                year_range[0],
                datetime(int(leap_year), 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            )
            self.assertEqual(
                year_range[1],
                datetime(int(leap_year), 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            )

    # ========== YEAR TRANSITION CASES ==========

    def test_new_year_edge_case(self):
        """Test with reference date at beginning of year."""
        result = get_n_years_date_range(self.ref_date_2025, count=2)

        expected = {
            "2025": (
                datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "2024": (
                datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "2023": (
                datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
        }

        self.assertEqual(result, expected)

    def test_end_of_year_edge_case(self):
        """Test with reference date at end of year."""
        ref_date = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        result = get_n_years_date_range(ref_date, count=1)

        expected = {
            "2024": (
                datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "2023": (
                datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
        }

        self.assertEqual(result, expected)

    # ========== TIMEZONE AND PRECISION TESTS ==========

    def test_timezone_consistency(self):
        """Test that all datetime objects use UTC timezone."""
        result = get_n_years_date_range(self.ref_date_2024, count=3)

        for start_date, end_date in result.values():
            self.assertEqual(start_date.tzinfo, timezone.utc)
            self.assertEqual(end_date.tzinfo, timezone.utc)

    def test_datetime_precision(self):
        """Test datetime precision for start and end times."""
        result = get_n_years_date_range(self.ref_date_2024, count=2)

        for start_date, end_date in result.values():
            # Start dates should be at exact midnight
            self.assertEqual(start_date.hour, 0)
            self.assertEqual(start_date.minute, 0)
            self.assertEqual(start_date.second, 0)
            self.assertEqual(start_date.microsecond, 0)

            # End dates should be at 23:59:59
            self.assertEqual(end_date.hour, 23)
            self.assertEqual(end_date.minute, 59)
            self.assertEqual(end_date.second, 59)
            self.assertEqual(end_date.microsecond, 0)

    def test_year_boundaries_precision(self):
        """Test that year boundaries are exactly at year start/end."""
        result = get_n_years_date_range(self.ref_date_2024, count=1)

        for year_str, (start_date, end_date) in result.items():
            year_int = int(year_str)

            # Start should be January 1st
            self.assertEqual(start_date.month, 1)
            self.assertEqual(start_date.day, 1)
            self.assertEqual(start_date.year, year_int)

            # End should be December 31st
            self.assertEqual(end_date.month, 12)
            self.assertEqual(end_date.day, 31)
            self.assertEqual(end_date.year, year_int)

    # ========== DATA STRUCTURE AND TYPE TESTS ==========

    def test_return_type_structure(self):
        """Test that return type is correct dictionary structure."""
        result = get_n_years_date_range(self.ref_date_2024, count=2)

        # Should be a dictionary
        self.assertIsInstance(result, dict)

        # Each key should be a string (year)
        for key in result:
            self.assertIsInstance(key, str)
            # Should be a valid 4-digit year
            self.assertTrue(key.isdigit())
            self.assertEqual(len(key), 4)

        # Each value should be a tuple with 2 datetime objects
        for value in result.values():
            self.assertIsInstance(value, tuple)
            self.assertEqual(len(value), 2)
            self.assertIsInstance(value[0], datetime)
            self.assertIsInstance(value[1], datetime)
            # Start should be before end
            self.assertLess(value[0], value[1])

    def test_chronological_order_validation(self):
        """Test that years are in correct chronological relationship."""
        result = get_n_years_date_range(self.ref_date_2024, count=5)

        years = sorted(result.keys(), reverse=True)  # Most recent first

        for i in range(len(years) - 1):
            current_year = int(years[i])
            next_year = int(years[i + 1])

            # Each year should be exactly 1 year before the previous
            self.assertEqual(current_year - next_year, 1)

    # ========== REFERENCE DATE INDEPENDENCE TESTS ==========

    def test_reference_date_time_independence(self):
        """Test that time component of reference date doesn't affect results."""
        ref_morning = datetime(2024, 6, 15, 8, 0, 0, tzinfo=timezone.utc)
        ref_evening = datetime(2024, 6, 15, 20, 0, 0, tzinfo=timezone.utc)
        ref_midnight = datetime(2024, 6, 15, 0, 0, 0, tzinfo=timezone.utc)

        result_morning = get_n_years_date_range(ref_morning, count=2)
        result_evening = get_n_years_date_range(ref_evening, count=2)
        result_midnight = get_n_years_date_range(ref_midnight, count=2)

        # All should be identical since only year matters
        self.assertEqual(result_morning, result_evening)
        self.assertEqual(result_evening, result_midnight)

    def test_reference_date_month_independence(self):
        """Test that month/day of reference date doesn't affect results."""
        ref_jan = datetime(2024, 1, 1, tzinfo=timezone.utc)
        ref_jun = datetime(2024, 6, 15, tzinfo=timezone.utc)
        ref_dec = datetime(2024, 12, 31, tzinfo=timezone.utc)

        result_jan = get_n_years_date_range(ref_jan, count=2)
        result_jun = get_n_years_date_range(ref_jun, count=2)
        result_dec = get_n_years_date_range(ref_dec, count=2)

        # All should be identical since only year matters
        self.assertEqual(result_jan, result_jun)
        self.assertEqual(result_jun, result_dec)

    # ========== PERFORMANCE AND CONSISTENCY TESTS ==========

    def test_performance_large_count(self):
        """Test performance with large count values."""
        import time

        start_time = time.time()
        result = get_n_years_date_range(self.ref_date_2024, count=100)
        end_time = time.time()

        # Should complete in reasonable time (less than 1 second)
        self.assertLess(end_time - start_time, 1.0)

        # Should have correct number of years
        self.assertEqual(len(result), 101)  # Current year + 100 previous

    def test_consistency_across_calls(self):
        """Test that multiple calls return consistent results."""
        result1 = get_n_years_date_range(self.ref_date_2024, count=3)
        result2 = get_n_years_date_range(self.ref_date_2024, count=3)
        result3 = get_n_years_date_range(self.ref_date_2024, count=3)

        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)

    def test_immutability(self):
        """Test that returned datetime objects are immutable references."""
        result1 = get_n_years_date_range(self.ref_date_2024, count=2)
        result2 = get_n_years_date_range(self.ref_date_2024, count=2)

        # Objects should be equal but not the same instance
        for year in result1:
            self.assertEqual(result1[year], result2[year])
            # Start dates should be separate objects
            self.assertIsNot(result1[year][0], result2[year][0])
            # End dates should be separate objects
            self.assertIsNot(result1[year][1], result2[year][1])

    # ========== EXTREME CASES ==========

    def test_extreme_past_years(self):
        """Test with reference date far in the past."""
        ref_date = datetime(1900, 1, 1, tzinfo=timezone.utc)
        result = get_n_years_date_range(ref_date, count=5)

        expected_years = ["1900", "1899", "1898", "1897", "1896", "1895"]

        self.assertEqual(len(result), 6)
        self.assertEqual(set(result.keys()), set(expected_years))

    def test_extreme_future_years(self):
        """Test with reference date far in the future."""
        ref_date = datetime(3000, 1, 1, tzinfo=timezone.utc)
        result = get_n_years_date_range(ref_date, count=2)

        expected_years = ["3000", "2999", "2998"]

        self.assertEqual(len(result), 3)
        self.assertEqual(set(result.keys()), set(expected_years))

    # ========== ERROR HANDLING TESTS ==========

    def test_invalid_reference_date_type(self):
        """Test behavior with invalid reference date type."""
        with self.assertRaises(AttributeError):
            # This should raise an error due to string instead of datetime
            get_n_years_date_range("not a date", count=1)  # type: ignore

    def test_none_reference_date(self):
        """Test behavior with None reference date."""
        with self.assertRaises(AttributeError):
            # This should raise an error due to None instead of datetime
            get_n_years_date_range(None, count=1)  # type: ignore

    def test_float_count(self):
        """Test behavior with float count (should work as int)."""
        # This should work because Python handles float to int conversion in loops
        result = get_n_years_date_range(self.ref_date_2024, count=2.5)  # type: ignore

        # Should treat 2.5 as 2 in the while loop
        expected_years = ["2024", "2023", "2022"]
        self.assertEqual(len(result), 3)
        self.assertEqual(set(result.keys()), set(expected_years))

    def test_string_count(self):
        """Test behavior with string count."""
        with self.assertRaises(TypeError):
            # This should raise TypeError due to string operations
            get_n_years_date_range(self.ref_date_2024, count="invalid")  # type: ignore
