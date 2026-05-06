# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

"""Test cases for add_date_searchbar_filters method."""

from datetime import datetime, timezone
from unittest.mock import patch

from odoo import _
from odoo.addons.website_common.controllers.portal import CommonPortalController
from odoo.tests import TransactionCase, tagged


@tagged("add_date_searchbar_filters", "portal", "website_common")
class TestAddDateSearchbarFilters(TransactionCase):
    """Test cases for the add_date_searchbar_filters method."""

    def test_returns_dictionary_with_basic_structure(self):
        """Should return a dictionary with divider and header entries."""
        result = CommonPortalController.add_date_searchbar_filters(
            "date_field", "Test Date"
        )

        self.assertIsInstance(result, dict)
        self.assertIn("date_field_divider", result)
        self.assertIn("date_field_header", result)

        # Verify divider structure
        divider = result["date_field_divider"]
        self.assertEqual(divider["label"], _("Date Start"))
        self.assertEqual(divider["domain"], [])
        self.assertEqual(divider["sequence"], 2)
        self.assertEqual(divider["type"], "divider")

        # Verify header structure (items key should NOT be present)
        header = result["date_field_header"]
        self.assertEqual(header["label"], "Test Date")
        self.assertEqual(header["domain"], [])
        self.assertEqual(header["sequence"], 3)
        self.assertEqual(header["type"], "header")
        self.assertNotIn("items", header)  # Updated: items key should not exist

    def test_header_structure_without_items_key(self):
        """Should verify that header structure does not include 'items' key."""
        result = CommonPortalController.add_date_searchbar_filters("test_field", "Test")

        header = result["test_field_header"]
        expected_keys = {"label", "domain", "sequence", "type"}
        actual_keys = set(header.keys())

        self.assertEqual(actual_keys, expected_keys)
        self.assertNotIn("items", header)

    @patch(
        "odoo.addons.website_common.controllers.portal.get_today_yesterday_last_7_days"
    )
    def test_includes_today_yesterday_last_7_days_filters(self, mock_get_today):
        """Should include filters for Today, Yesterday, and Last 7 days."""
        mock_today = datetime(2025, 10, 6, 0, 0, 0, tzinfo=timezone.utc)
        mock_yesterday = datetime(2025, 10, 5, 0, 0, 0, tzinfo=timezone.utc)
        mock_week_start = datetime(2025, 9, 29, 0, 0, 0, tzinfo=timezone.utc)

        mock_get_today.return_value = {
            _("Today"): (
                mock_today,
                datetime(2025, 10, 6, 23, 59, 59, tzinfo=timezone.utc),
            ),
            _("Yesterday"): (
                mock_yesterday,
                datetime(2025, 10, 5, 23, 59, 59, tzinfo=timezone.utc),
            ),
            _("Last 7 days"): (
                mock_week_start,
                datetime(2025, 10, 5, 23, 59, 59, tzinfo=timezone.utc),
            ),
        }

        result = CommonPortalController.add_date_searchbar_filters(
            "date_field", "Test Date"
        )

        # Check that Today filter exists
        self.assertIn("today", result)
        today_filter = result["today"]
        self.assertEqual(today_filter["label"], _("Today"))
        self.assertEqual(today_filter["parent"], "date_field_header")
        self.assertIn(("date_field", ">=", mock_today), today_filter["domain"])

        # Check that Yesterday filter exists
        self.assertIn("yesterday", result)
        yesterday_filter = result["yesterday"]
        self.assertEqual(yesterday_filter["label"], _("Yesterday"))
        self.assertEqual(yesterday_filter["parent"], "date_field_header")
        self.assertIn(("date_field", ">=", mock_yesterday), yesterday_filter["domain"])

        # Check that Last 7 days filter exists
        self.assertIn("last_7_days", result)
        week_filter = result["last_7_days"]
        self.assertEqual(week_filter["label"], _("Last 7 days"))
        self.assertEqual(week_filter["parent"], "date_field_header")
        self.assertIn(("date_field", ">=", mock_week_start), week_filter["domain"])

    @patch("odoo.addons.website_common.controllers.portal.get_n_months_date_range")
    def test_includes_month_filters(self, mock_get_months):
        """Should include filters for current and previous months."""
        mock_get_months.return_value = {
            "October 2025": (
                datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2025, 10, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "September 2025": (
                datetime(2025, 9, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2025, 9, 30, 23, 59, 59, tzinfo=timezone.utc),
            ),
        }

        result = CommonPortalController.add_date_searchbar_filters(
            "date_field", "Test Date"
        )

        # Check that month filters exist
        self.assertIn("october_2025", result)
        self.assertIn("september_2025", result)

        oct_filter = result["october_2025"]
        self.assertEqual(oct_filter["label"], "October 2025")
        self.assertEqual(oct_filter["parent"], "date_field_header")

    @patch("odoo.addons.website_common.controllers.portal.get_quarters_date_range")
    def test_includes_quarter_filters(self, mock_get_quarters):
        """Should include filters for quarters."""
        mock_get_quarters.return_value = {
            _("Q1"): (
                datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2025, 3, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
            _("Q2"): (
                datetime(2025, 4, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2025, 6, 30, 23, 59, 59, tzinfo=timezone.utc),
            ),
        }

        result = CommonPortalController.add_date_searchbar_filters(
            "date_field", "Test Date"
        )

        # Check that quarter filters exist
        self.assertIn(_("Q1"), result)
        self.assertIn(_("Q2"), result)

        q1_filter = result[_("Q1")]
        self.assertEqual(q1_filter["label"], _("Q1"))
        self.assertEqual(q1_filter["parent"], "date_field_header")

    @patch("odoo.addons.website_common.controllers.portal.get_n_years_date_range")
    def test_includes_year_filters(self, mock_get_years):
        """Should include filters for current and previous years."""
        mock_get_years.return_value = {
            "2025": (
                datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
            "2024": (
                datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            ),
        }

        result = CommonPortalController.add_date_searchbar_filters(
            "date_field", "Test Date"
        )

        # Check that year filters exist
        self.assertIn(_("2025"), result)
        self.assertIn(_("2024"), result)

        year_filter = result[_("2025")]
        self.assertEqual(year_filter["label"], _("2025"))
        self.assertEqual(year_filter["parent"], "date_field_header")

    def test_custom_sequence_numbering(self):
        """Should respect custom sequence numbering."""
        result = CommonPortalController.add_date_searchbar_filters(
            "date_field", "Test Date", sequence=10
        )

        # Divider should be sequence + 1
        self.assertEqual(result["date_field_divider"]["sequence"], 11)
        # Header should be sequence + 2
        self.assertEqual(result["date_field_header"]["sequence"], 12)

        # All other filters should have sequences >= 13
        other_filters = [
            k
            for k in result.keys()
            if k not in ["date_field_divider", "date_field_header"]
        ]
        for filter_key in other_filters:
            self.assertGreaterEqual(result[filter_key]["sequence"], 13)

    def test_custom_field_name_in_domains(self):
        """Should use custom field name in filter domains."""
        custom_field = "custom_date_field"
        result = CommonPortalController.add_date_searchbar_filters(
            custom_field, "Custom Date"
        )

        # Check that all filters use the custom field name in their domains
        for _key, filter_config in result.items():
            if filter_config.get("domain"):
                for condition in filter_config["domain"]:
                    if isinstance(condition, tuple) and len(condition) >= 1:
                        self.assertEqual(condition[0], custom_field)

    def test_custom_field_title_in_header(self):
        """Should use custom field title in header label."""
        custom_title = "My Custom Date Field"
        result = CommonPortalController.add_date_searchbar_filters(
            "date_field", custom_title
        )

        header = result["date_field_header"]
        self.assertEqual(header["label"], custom_title)

    def test_language_code_parameter(self):
        """Should pass language code to month range function."""
        with patch(
            "odoo.addons.website_common.controllers.portal.get_n_months_date_range"
        ) as mock_months:
            mock_months.return_value = {}

            CommonPortalController.add_date_searchbar_filters(
                "date_field", "Test Date", lang_code="es"
            )

            # Verify that get_n_months_date_range was called with lang_code
            mock_months.assert_called_once()
            call_args = mock_months.call_args
            self.assertEqual(call_args[1]["lang_code"], "es")

    def test_key_normalization_for_special_characters(self):
        """Should normalize keys with special characters properly."""
        with patch(
            "odoo.addons.website_common.controllers.portal.get_today_yesterday_last_7_days"
        ) as mock_today:
            mock_today.return_value = {
                "Tödäy": (datetime.now(timezone.utc), datetime.now(timezone.utc)),
                "Yéstërdày": (datetime.now(timezone.utc), datetime.now(timezone.utc)),
                "Last 7 days": (datetime.now(timezone.utc), datetime.now(timezone.utc)),
            }

            result = CommonPortalController.add_date_searchbar_filters(
                "date_field", "Test Date"
            )

            # Check that keys are properly normalized
            self.assertIn("today", result)
            self.assertIn("yesterday", result)
            self.assertIn("last_7_days", result)

    def test_all_filters_have_required_fields(self):
        """Should ensure all filters have required fields."""
        result = CommonPortalController.add_date_searchbar_filters(
            "date_field", "Test Date"
        )

        required_fields = ["label", "domain", "sequence"]

        for key, filter_config in result.items():
            if key not in ["date_field_divider", "date_field_header"]:
                for field in required_fields:
                    self.assertIn(
                        field, filter_config, f"Filter {key} missing field {field}"
                    )
                self.assertIn(
                    "parent", filter_config, f"Filter {key} missing parent field"
                )
                self.assertEqual(filter_config["parent"], "date_field_header")

    def test_domain_structure_is_correct(self):
        """Should ensure all filter domains have correct structure."""
        result = CommonPortalController.add_date_searchbar_filters(
            "date_field", "Test Date"
        )

        for key, filter_config in result.items():
            if key not in [
                "date_field_divider",
                "date_field_header",
            ] and filter_config.get("domain"):
                domain = filter_config["domain"]
                self.assertIsInstance(domain, list)
                self.assertEqual(len(domain), 2)  # Should have >= and <= conditions

                # Check >= condition
                gte_condition = domain[0]
                self.assertIsInstance(gte_condition, tuple)
                self.assertEqual(len(gte_condition), 3)
                self.assertEqual(gte_condition[0], "date_field")
                self.assertEqual(gte_condition[1], ">=")
                self.assertIsInstance(gte_condition[2], datetime)

                # Check <= condition
                lte_condition = domain[1]
                self.assertIsInstance(lte_condition, tuple)
                self.assertEqual(len(lte_condition), 3)
                self.assertEqual(lte_condition[0], "date_field")
                self.assertEqual(lte_condition[1], "<=")
                self.assertIsInstance(lte_condition[2], datetime)

    @patch("odoo.addons.website_common.controllers.portal.datetime")
    def test_uses_current_utc_time(self, mock_datetime):
        """Should use current UTC time for date calculations."""
        mock_now = datetime(2025, 10, 6, 15, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        with (
            patch(
                "odoo.addons.website_common.controllers.portal.get_n_months_date_range"
            ) as mock_months,
            patch(
                "odoo.addons.website_common.controllers.portal.get_n_years_date_range"
            ) as mock_years,
        ):
            mock_months.return_value = {}
            mock_years.return_value = {}

            CommonPortalController.add_date_searchbar_filters("date_field", "Test Date")

            # Verify that both functions were called with the mocked current time
            mock_months.assert_called_once()
            mock_years.assert_called_once()

            months_call_args = mock_months.call_args[0]
            years_call_args = mock_years.call_args[0]

            self.assertEqual(months_call_args[0], mock_now)
            self.assertEqual(years_call_args[0], mock_now)

    def test_sequence_increments_correctly(self):
        """Should increment sequences correctly for all filters."""
        result = CommonPortalController.add_date_searchbar_filters(
            "date_field", "Test Date", sequence=1
        )

        sequences = []
        for key, filter_config in result.items():
            sequences.append((key, filter_config["sequence"]))

        # Sort by sequence to verify order
        sequences.sort(key=lambda x: x[1])

        # Verify that sequences are sequential
        for i in range(1, len(sequences)):
            current_seq = sequences[i][1]
            previous_seq = sequences[i - 1][1]
            # Sequences should increment (not necessarily by 1 due to grouping)
            self.assertGreater(current_seq, previous_seq)

    def test_backward_compatibility_check(self):
        """Should verify the method works without breaking existing functionality."""
        # Test that the method still produces the expected basic structure
        result = CommonPortalController.add_date_searchbar_filters(
            "date_field", "Date Field"
        )

        # Ensure basic structure exists
        self.assertIn("date_field_divider", result)
        self.assertIn("date_field_header", result)

        # Ensure header doesn't have deprecated items key
        header = result["date_field_header"]
        self.assertNotIn("items", header)

        # Ensure all date-related filters are properly parented
        date_filters = [
            k
            for k in result.keys()
            if k not in ["date_field_divider", "date_field_header"]
        ]
        for filter_key in date_filters:
            self.assertEqual(result[filter_key]["parent"], "date_field_header")
