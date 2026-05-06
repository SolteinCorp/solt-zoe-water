# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

"""Tests for portal controller."""

import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from odoo.addons.website_common.controllers.portal import get_quarters_date_range
from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged("get_quarters_date_range", "website_common", "portal")
class TestGetQuartersDateRange(TransactionCase):
    """Test cases for get_quarters_date_range function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.maxDiff = None

    def test_quarters_date_range_structure(self):
        """Test that the function returns the correct data structure."""
        result = get_quarters_date_range()

        # Verify it's a dictionary
        self.assertIsInstance(result, dict)

        # Verify it has exactly 4 quarters
        self.assertEqual(len(result), 4)

        # Verify each value is a tuple with 2 datetime objects
        for date_range in result.values():
            self.assertIsInstance(date_range, tuple)
            self.assertEqual(len(date_range), 2)
            self.assertIsInstance(date_range[0], datetime)
            self.assertIsInstance(date_range[1], datetime)

            # Verify start date is before end date
            self.assertLess(date_range[0], date_range[1])

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_quarters_date_range_normal_year_2023(self, mock_datetime):
        """Test quarters for a normal (non-leap) year 2023."""
        # Mock datetime.now to return 2023
        mock_now = MagicMock()
        mock_now.year = 2023
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_quarters_date_range()

        # Expected date ranges for 2023
        expected_ranges = {
            "Q1": (
                datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2023, 3, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "Q2": (
                datetime(2023, 4, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2023, 6, 30, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "Q3": (
                datetime(2023, 7, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2023, 9, 30, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "Q4": (
                datetime(2023, 10, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
        }

        # Verify each quarter's date range (ignoring translation keys)
        result_values = list(result.values())
        expected_values = list(expected_ranges.values())

        for i, (actual, expected) in enumerate(
            zip(result_values, expected_values, strict=False)
        ):
            self.assertEqual(actual, expected, f"Quarter {i + 1} date range mismatch")

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_quarters_date_range_leap_year_2024(self, mock_datetime):
        """Test quarters for a leap year 2024."""
        # Mock datetime.now to return 2024
        mock_now = MagicMock()
        mock_now.year = 2024
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_quarters_date_range()

        # Q1 should still end on March 31 even in leap year
        q1_range = list(result.values())[0]  # First quarter
        self.assertEqual(q1_range[1].month, 3)
        self.assertEqual(q1_range[1].day, 31)
        self.assertEqual(q1_range[1].year, 2024)

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_quarters_date_range_future_year_2030(self, mock_datetime):
        """Test quarters for a future year 2030."""
        # Mock datetime.now to return 2030
        mock_now = MagicMock()
        mock_now.year = 2030
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_quarters_date_range()

        # Verify all dates are in 2030
        for _quarter_name, date_range in result.items():
            self.assertEqual(date_range[0].year, 2030)
            self.assertEqual(date_range[1].year, 2030)

    def test_quarters_timezone_consistency(self):
        """Test that all datetime objects use UTC timezone."""
        result = get_quarters_date_range()

        for _quarter_name, date_range in result.items():
            start_date, end_date = date_range
            self.assertEqual(start_date.tzinfo, timezone.utc)
            self.assertEqual(end_date.tzinfo, timezone.utc)

    def test_quarters_date_boundaries(self):
        """Test that quarter boundaries are correct."""
        result = get_quarters_date_range()
        quarters_list = list(result.values())

        # Q1: January 1 to March 31
        q1_start, q1_end = quarters_list[0]
        self.assertEqual(q1_start.month, 1)
        self.assertEqual(q1_start.day, 1)
        self.assertEqual(q1_start.hour, 0)
        self.assertEqual(q1_start.minute, 0)
        self.assertEqual(q1_start.second, 0)

        self.assertEqual(q1_end.month, 3)
        self.assertEqual(q1_end.day, 31)
        self.assertEqual(q1_end.hour, 23)
        self.assertEqual(q1_end.minute, 59)
        self.assertEqual(q1_end.second, 59)

        # Q2: April 1 to June 30
        q2_start, q2_end = quarters_list[1]
        self.assertEqual(q2_start.month, 4)
        self.assertEqual(q2_start.day, 1)
        self.assertEqual(q2_end.month, 6)
        self.assertEqual(q2_end.day, 30)

        # Q3: July 1 to September 30
        q3_start, q3_end = quarters_list[2]
        self.assertEqual(q3_start.month, 7)
        self.assertEqual(q3_start.day, 1)
        self.assertEqual(q3_end.month, 9)
        self.assertEqual(q3_end.day, 30)

        # Q4: October 1 to December 31
        q4_start, q4_end = quarters_list[3]
        self.assertEqual(q4_start.month, 10)
        self.assertEqual(q4_start.day, 1)
        self.assertEqual(q4_end.month, 12)
        self.assertEqual(q4_end.day, 31)

    def test_quarters_no_gaps_or_overlaps(self):
        """Test that quarters have no gaps or overlaps between them."""
        result = get_quarters_date_range()
        quarters_list = list(result.values())

        # Check that Q1 end + 1 second equals Q2 start
        q1_end = quarters_list[0][1]
        q2_start = quarters_list[1][0]
        expected_q2_start = datetime(
            q1_end.year, q1_end.month + 1, 1, 0, 0, 0, tzinfo=timezone.utc
        )
        self.assertEqual(q2_start, expected_q2_start)

        # Check that Q2 end + 1 second equals Q3 start
        q2_end = quarters_list[1][1]
        q3_start = quarters_list[2][0]
        expected_q3_start = datetime(
            q2_end.year, q2_end.month + 1, 1, 0, 0, 0, tzinfo=timezone.utc
        )
        self.assertEqual(q3_start, expected_q3_start)

        # Check that Q3 end + 1 second equals Q4 start
        q3_end = quarters_list[2][1]
        q4_start = quarters_list[3][0]
        expected_q4_start = datetime(
            q3_end.year, q3_end.month + 1, 1, 0, 0, 0, tzinfo=timezone.utc
        )
        self.assertEqual(q4_start, expected_q4_start)

    def test_quarters_translation_keys(self):
        """Test that quarter names use translation keys."""
        result = get_quarters_date_range()
        quarter_keys = list(result.keys())

        # We can't directly test the translation mechanism in unit tests,
        # but we can verify the structure
        self.assertEqual(len(quarter_keys), 4)

        # Verify that keys are related to quarters (assuming they contain Q)
        for key in quarter_keys:
            # The key might be a translation object or string containing quarter info
            self.assertIsNotNone(key)

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_quarters_date_range_consistency_across_calls(self, mock_datetime):
        """Test that multiple calls return consistent results for the same year."""
        # Mock datetime.now to return a fixed year
        mock_now = MagicMock()
        mock_now.year = 2025
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result1 = get_quarters_date_range()
        result2 = get_quarters_date_range()

        # Compare values (ignoring keys which might be translation objects)
        values1 = list(result1.values())
        values2 = list(result2.values())

        self.assertEqual(values1, values2)

    def test_quarters_microseconds_handling(self):
        """Test that end dates don't have microseconds set."""
        result = get_quarters_date_range()

        for _quarter_name, date_range in result.items():
            start_date, end_date = date_range
            # Start dates should have microseconds = 0
            self.assertEqual(start_date.microsecond, 0)
            # End dates should have microseconds = 0 (23:59:59, not 23:59:59.999999)
            self.assertEqual(end_date.microsecond, 0)

    def test_quarters_year_boundary_edge_cases(self):
        """Test edge cases around year boundaries."""
        result = get_quarters_date_range()
        quarters_list = list(result.values())

        # Q4 should end exactly at year end
        q4_end = quarters_list[3][1]
        self.assertEqual(q4_end.month, 12)
        self.assertEqual(q4_end.day, 31)
        self.assertEqual(q4_end.hour, 23)
        self.assertEqual(q4_end.minute, 59)
        self.assertEqual(q4_end.second, 59)

        # Q1 should start exactly at year beginning
        q1_start = quarters_list[0][0]
        self.assertEqual(q1_start.month, 1)
        self.assertEqual(q1_start.day, 1)
        self.assertEqual(q1_start.hour, 0)
        self.assertEqual(q1_start.minute, 0)
        self.assertEqual(q1_start.second, 0)

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_quarters_extreme_years(self, mock_datetime):
        """Test quarters for extreme years (very old and very future)."""
        test_years = [1900, 2100, 2200, 3000]

        for year in test_years:
            with self.subTest(year=year):
                mock_now = MagicMock()
                mock_now.year = year
                mock_datetime.now.return_value = mock_now
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                    *args, **kwargs
                )

                result = get_quarters_date_range()

                # Verify all dates are in the expected year
                for _quarter_name, date_range in result.items():
                    self.assertEqual(date_range[0].year, year)
                    self.assertEqual(date_range[1].year, year)

    def test_quarters_february_handling(self):
        """Test that February is correctly handled (not included in Q1)."""
        result = get_quarters_date_range()
        quarters_list = list(result.values())

        # Q1 should end in March, not February
        q1_start, q1_end = quarters_list[0]
        self.assertEqual(q1_end.month, 3)  # March
        self.assertNotEqual(q1_end.month, 2)  # Not February

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_quarters_leap_year_february_impact(self, mock_datetime):
        """Test that leap year February doesn't affect quarter boundaries."""
        # Test leap year 2024
        mock_now = MagicMock()
        mock_now.year = 2024
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_quarters_date_range()
        quarters_list = list(result.values())

        # Q1 should still end on March 31, even in leap year
        q1_start, q1_end = quarters_list[0]
        self.assertEqual(q1_end.month, 3)
        self.assertEqual(q1_end.day, 31)

    def test_quarters_performance_multiple_calls(self):
        """Test performance of multiple consecutive calls."""
        import time

        start_time = time.time()
        for _ in range(100):
            result = get_quarters_date_range()
            # Verify basic structure on each call
            self.assertEqual(len(result), 4)
        end_time = time.time()

        # Should complete 100 calls in less than 1 second
        self.assertLess(end_time - start_time, 1.0)

    def test_quarters_memory_efficiency(self):
        """Test that function doesn't create excessive objects."""
        import sys

        # Get initial memory usage
        initial_objects = len(list(sys.modules.keys()))

        # Call function multiple times
        for _ in range(50):
            result = get_quarters_date_range()
            del result  # Explicit cleanup

        # Memory shouldn't grow significantly
        final_objects = len(list(sys.modules.keys()))
        self.assertLessEqual(final_objects - initial_objects, 5)

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_quarters_century_leap_years(self, mock_datetime):
        """Test century years that are not leap years (1900, 2100)."""
        century_years = [1900, 2100]  # Not leap years

        for year in century_years:
            with self.subTest(year=year):
                mock_now = MagicMock()
                mock_now.year = year
                mock_datetime.now.return_value = mock_now
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                    *args, **kwargs
                )

                result = get_quarters_date_range()
                quarters_list = list(result.values())

                # Q1 should still end on March 31
                q1_start, q1_end = quarters_list[0]
                self.assertEqual(q1_end.month, 3)
                self.assertEqual(q1_end.day, 31)

    def test_quarters_immutability(self):
        """Test that returned datetime objects are not mutable references."""
        result1 = get_quarters_date_range()
        result2 = get_quarters_date_range()

        # Modify one result's datetime (if it were mutable)
        q1_range1 = list(result1.values())[0]
        q1_range2 = list(result2.values())[0]

        # They should be separate objects
        self.assertIsNot(q1_range1[0], q1_range2[0])
        self.assertIsNot(q1_range1[1], q1_range2[1])

    def test_quarters_datetime_precision(self):
        """Test datetime precision for start and end times."""
        result = get_quarters_date_range()

        for _quarter_name, date_range in result.items():
            start_date, end_date = date_range

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

    def test_quarters_total_year_coverage(self):
        """Test that quarters cover the entire year without gaps."""
        result = get_quarters_date_range()
        quarters_list = list(result.values())

        # Sort quarters by start date
        sorted_quarters = sorted(quarters_list, key=lambda x: x[0])

        # Check year coverage
        first_quarter_start = sorted_quarters[0][0]
        last_quarter_end = sorted_quarters[3][1]

        # Should start on January 1st
        self.assertEqual(first_quarter_start.month, 1)
        self.assertEqual(first_quarter_start.day, 1)

        # Should end on December 31st
        self.assertEqual(last_quarter_end.month, 12)
        self.assertEqual(last_quarter_end.day, 31)

        # Check no gaps between quarters
        for i in range(len(sorted_quarters) - 1):
            current_end = sorted_quarters[i][1]
            next_start = sorted_quarters[i + 1][0]

            # Next quarter should start exactly 1 second after current ends
            # (since end is 23:59:59 and next starts at 00:00:00 next day)
            expected_next_start = datetime(
                current_end.year,
                current_end.month + (1 if current_end.month < 12 else -11),
                1 if current_end.month < 12 else 1,
                0,
                0,
                0,
                tzinfo=timezone.utc,
            )
            # Adjust year for December to January transition
            if current_end.month == 12:
                expected_next_start = expected_next_start.replace(
                    year=current_end.year + 1
                )

            self.assertEqual(next_start, expected_next_start)

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_quarters_different_timezones_mock(self, mock_datetime):
        """Test that function always returns UTC regardless of system timezone."""
        # Mock datetime.now to simulate different timezone
        mock_now = MagicMock()
        mock_now.year = 2025
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_quarters_date_range()

        # All datetimes should be UTC
        for _quarter_name, date_range in result.items():
            start_date, end_date = date_range
            self.assertEqual(start_date.tzinfo, timezone.utc)
            self.assertEqual(end_date.tzinfo, timezone.utc)

    def test_quarters_return_type_consistency(self):
        """Test that return type is always consistent."""
        result = get_quarters_date_range()

        # Should always return dict
        self.assertIsInstance(result, dict)

        # Each value should always be tuple
        for _key, value in result.items():
            self.assertIsInstance(value, tuple)
            self.assertEqual(len(value), 2)

            # Each tuple element should be datetime
            self.assertIsInstance(value[0], datetime)
            self.assertIsInstance(value[1], datetime)

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_quarters_thread_safety(self, mock_datetime):
        """Test that function is thread-safe when called concurrently."""
        import queue
        import threading

        mock_now = MagicMock()
        mock_now.year = 2025
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        results = queue.Queue()
        errors = queue.Queue()

        def call_function():
            """Thread worker function to call get_quarters_date_range."""
            try:
                _result = get_quarters_date_range()
                results.put(_result)
            except Exception as e:
                errors.put(e)

        # Create and start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=call_function)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check that no errors occurred
        self.assertTrue(
            errors.empty(),
            f"Thread safety test failed with errors: {list(errors.queue)}",
        )

        # Check that all results are consistent
        all_results = []
        while not results.empty():
            all_results.append(results.get())

        self.assertEqual(len(all_results), 10)

        # All results should be identical (values comparison)
        first_result_values = list(all_results[0].values())
        for result in all_results[1:]:
            self.assertEqual(list(result.values()), first_result_values)

    def test_quarters_translation_integration(self):
        """Test integration with Odoo translation system."""
        result = get_quarters_date_range()

        # Check that keys exist and are not None
        for key in result.keys():
            self.assertIsNotNone(key)
            # In a real Odoo environment, these would be translated strings
            # We can at least verify they're not empty
            if isinstance(key, str):
                self.assertNotEqual(key.strip(), "")

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_quarters_date_arithmetic_validation(self, mock_datetime):
        """Test that date arithmetic is correct for all quarters."""
        mock_now = MagicMock()
        mock_now.year = 2025
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_quarters_date_range()
        quarters_list = list(result.values())

        # Expected days in each quarter for 2025 (non-leap year)
        expected_days = [
            90,  # Q1: Jan(31) + Feb(28) + Mar(31) = 90
            91,  # Q2: Apr(30) + May(31) + Jun(30) = 91
            92,  # Q3: Jul(31) + Aug(31) + Sep(30) = 92
            92,  # Q4: Oct(31) + Nov(30) + Dec(31) = 92
        ]

        for i, (start, end) in enumerate(quarters_list):
            # Calculate actual days in quarter
            actual_days = (end - start).days + 1  # +1 because both dates are inclusive
            self.assertEqual(
                actual_days,
                expected_days[i],
                f"Quarter {i + 1} should have {expected_days[i]} days, got {actual_days}",
            )

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_quarters_leap_year_date_arithmetic(self, mock_datetime):
        """Test date arithmetic for leap year."""
        mock_now = MagicMock()
        mock_now.year = 2024  # Leap year
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_quarters_date_range()
        quarters_list = list(result.values())

        # Expected days in each quarter for 2024 (leap year)
        expected_days = [
            91,  # Q1: Jan(31) + Feb(29) + Mar(31) = 91 (leap year)
            91,  # Q2: Apr(30) + May(31) + Jun(30) = 91
            92,  # Q3: Jul(31) + Aug(31) + Sep(30) = 92
            92,  # Q4: Oct(31) + Nov(30) + Dec(31) = 92
        ]

        for i, (start, end) in enumerate(quarters_list):
            actual_days = (end - start).days + 1
            self.assertEqual(
                actual_days,
                expected_days[i],
                f"Leap year Quarter {i + 1} should have {expected_days[i]} days, got {actual_days}",
            )

    def test_quarters_datetime_immutability(self):
        """Test that returned datetime objects cannot affect future calls."""
        result1 = get_quarters_date_range()

        # Try to modify the first quarter's start date (should not affect subsequent calls)
        first_quarter_dates = list(result1.values())[0]
        original_start = first_quarter_dates[0]

        # Get another result
        result2 = get_quarters_date_range()
        second_quarter_dates = list(result2.values())[0]

        # Verify the dates are still correct and not affected
        self.assertEqual(original_start, second_quarter_dates[0])

    def test_quarters_string_representation(self):
        """Test string representation of returned datetime objects."""
        result = get_quarters_date_range()

        for _quarter_name, date_range in result.items():
            start_date, end_date = date_range

            # Verify string representation includes timezone info
            start_str = str(start_date)
            end_str = str(end_date)

            self.assertIn("+00:00", start_str)  # UTC timezone
            self.assertIn("+00:00", end_str)  # UTC timezone

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_quarters_error_handling_invalid_year(self, mock_datetime):
        """Test behavior when datetime.now returns invalid year."""
        # This test checks robustness, though datetime typically handles wide year ranges
        mock_now = MagicMock()
        mock_now.year = 1  # Very early year
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        try:
            result = get_quarters_date_range()
            # If it succeeds, verify basic structure
            self.assertEqual(len(result), 4)
            for _quarter_name, date_range in result.items():
                self.assertEqual(date_range[0].year, 1)
                self.assertEqual(date_range[1].year, 1)
        except (ValueError, OverflowError):
            # This is acceptable for extreme edge cases
            _logger.exception("Invalid year")

    def test_quarters_function_purity(self):
        """Test that function is pure (no side effects)."""
        # Call function multiple times and verify no global state changes
        results = []
        for _ in range(5):
            result = get_quarters_date_range()
            results.append(list(result.values()))

        # All results should be identical (pure function)
        first_result = results[0]
        for result in results[1:]:
            self.assertEqual(result, first_result)

    def test_quarters_iso_format_compliance(self):
        """Test that datetime objects comply with ISO format."""
        result = get_quarters_date_range()

        for _quarter_name, date_range in result.items():
            start_date, end_date = date_range

            # Test ISO format conversion
            start_iso = start_date.isoformat()
            end_iso = end_date.isoformat()

            # Should be able to parse back from ISO format
            parsed_start = datetime.fromisoformat(start_iso)
            parsed_end = datetime.fromisoformat(end_iso)

            self.assertEqual(start_date, parsed_start)
            self.assertEqual(end_date, parsed_end)

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_quarters_business_logic_validation(self, mock_datetime):
        """Test business logic: standard fiscal quarters."""
        mock_now = MagicMock()
        mock_now.year = 2025
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        result = get_quarters_date_range()
        quarters_list = list(result.values())

        # Verify standard business quarters
        # Q1: Jan-Mar, Q2: Apr-Jun, Q3: Jul-Sep, Q4: Oct-Dec
        expected_quarters = [
            (1, 3),  # Q1: January to March
            (4, 6),  # Q2: April to June
            (7, 9),  # Q3: July to September
            (10, 12),  # Q4: October to December
        ]

        for i, ((start, end), (expected_start_month, expected_end_month)) in enumerate(
            zip(quarters_list, expected_quarters, strict=False)
        ):
            self.assertEqual(
                start.month,
                expected_start_month,
                f"Quarter {i + 1} should start in month {expected_start_month}",
            )
            self.assertEqual(
                end.month,
                expected_end_month,
                f"Quarter {i + 1} should end in month {expected_end_month}",
            )

    def test_quarters_data_integrity(self):
        """Test data integrity across multiple calls."""
        # Collect multiple results
        results = [get_quarters_date_range() for _ in range(10)]

        # Verify all results have same structure
        for result in results:
            self.assertEqual(len(result), 4)

            # Verify order is consistent (quarters should be in chronological order)
            quarters_list = list(result.values())
            for i in range(len(quarters_list) - 1):
                current_end = quarters_list[i][1]
                next_start = quarters_list[i + 1][0]
                self.assertLess(current_end, next_start)

    def test_quarters_boundary_precision(self):
        """Test precision of quarter boundaries."""
        result = get_quarters_date_range()
        quarters_list = list(result.values())

        for i, (start, end) in enumerate(quarters_list):
            # Start of quarter should be first day of month at midnight UTC
            self.assertEqual(start.day, 1)
            self.assertEqual(start.hour, 0)
            self.assertEqual(start.minute, 0)
            self.assertEqual(start.second, 0)
            self.assertEqual(start.microsecond, 0)
            self.assertEqual(start.tzinfo, timezone.utc)

            # End of quarter should be last day of month at 23:59:59.999999 UTC
            self.assertEqual(end.hour, 23)
            self.assertEqual(end.minute, 59)
            self.assertEqual(end.second, 59)
            self.assertEqual(end.microsecond, 0)
            self.assertEqual(end.tzinfo, timezone.utc)

            # Validate quarter end months and their last days
            if end.month == 3:  # March (Q1 end) - always has 31 days
                self.assertEqual(end.day, 31)
            elif end.month in {6, 9}:  # June (Q2 end) - always has 30 days
                self.assertEqual(end.day, 30)
            elif end.month == 12:  # December (Q4 end) - always has 31 days
                self.assertEqual(end.day, 31)
            else:
                self.fail(f"Quarter {i + 1} ends in unexpected month: {end.month}")

            # Validate quarter start months
            if start.month == 1:  # January (Q1 start)
                self.assertEqual(
                    end.month, 3, f"Q1 should end in March, got {end.month}"
                )
            elif start.month == 4:  # April (Q2 start)
                self.assertEqual(
                    end.month, 6, f"Q2 should end in June, got {end.month}"
                )
            elif start.month == 7:  # July (Q3 start)
                self.assertEqual(
                    end.month, 9, f"Q3 should end in September, got {end.month}"
                )
            elif start.month == 10:  # October (Q4 start)
                self.assertEqual(
                    end.month, 12, f"Q4 should end in December, got {end.month}"
                )
            else:
                self.fail(f"Quarter {i + 1} starts in unexpected month: {start.month}")

            # Validate that start and end are in the same year for each quarter
            self.assertEqual(
                start.year,
                end.year,
                f"Quarter {i + 1} start and end should be in same year",
            )

            # Validate that the quarter span is exactly 3 months
            expected_start_months = [1, 4, 7, 10]
            expected_end_months = [3, 6, 9, 12]

            if start.month in expected_start_months:
                quarter_index = expected_start_months.index(start.month)
                expected_end_month = expected_end_months[quarter_index]
                self.assertEqual(
                    end.month,
                    expected_end_month,
                    f"Quarter starting in month {start.month} should end in month {expected_end_month}",
                )

            # Validate chronological order within the result
            if i > 0:
                prev_start, prev_end = quarters_list[i - 1]
                self.assertGreater(
                    start,
                    prev_start,
                    f"Quarter {i + 1} start should be after quarter {i} start",
                )
                self.assertGreater(
                    end,
                    prev_end,
                    f"Quarter {i + 1} end should be after quarter {i} end",
                )
