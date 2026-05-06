# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

"""Comprehensive test cases for change_previous_next_record_url function."""

from unittest.mock import MagicMock, patch

from odoo.addons.website_common.utils import search as search_module
from odoo.addons.website_common.utils.search import change_previous_next_record_url
from odoo.tests import TransactionCase, tagged


@tagged("search_utils", "website_common", "post_install", "-at_install")
class TestChangePreviousNextRecordUrl(TransactionCase):
    """Test cases for change_previous_next_record_url function."""

    @classmethod
    def setUpClass(cls):
        """Set up test data for all tests."""
        super().setUpClass()

        # Create test partners for navigation history
        cls.partners = cls.env["res.partner"].create(
            [{"name": f"Partner {i}"} for i in range(1, 6)]
        )

        # Store IDs for easier access
        cls.partner_ids = cls.partners.ids

    def setUp(self):
        """Set up mock request for each test."""
        super().setUp()

        # Mock request object
        self.mock_request = MagicMock()
        self.mock_request.session = {}

    def test_record_in_middle_of_history_returns_both_urls(self):
        """Should return both prev and next URLs when record is in middle of history."""
        # Set up history with record in middle
        self.mock_request.session["product_history"] = [
            self.partner_ids[0],
            self.partner_ids[1],  # Current record
            self.partner_ids[2],
        ]

        with patch.object(search_module, "request", self.mock_request):
            values = {}
            result = change_previous_next_record_url(
                values=values,
                model_instance=self.partners[1],
                url="/website/partner",
                history_name="product_history",
            )

            # Should have both prev and next URLs
            self.assertEqual(
                result["prev_record"], f"/website/partner/{self.partner_ids[0]}"
            )
            self.assertEqual(
                result["next_record"], f"/website/partner/{self.partner_ids[2]}"
            )

    def test_record_at_beginning_of_history_returns_only_next_url(self):
        """Should return False for prev_record when at beginning of history."""
        # Set up history with record at beginning
        self.mock_request.session["product_history"] = [
            self.partner_ids[0],  # Current record (first)
            self.partner_ids[1],
            self.partner_ids[2],
        ]

        with patch.object(search_module, "request", self.mock_request):
            values = {}
            result = change_previous_next_record_url(
                values=values,
                model_instance=self.partners[0],
                url="/website/partner",
                history_name="product_history",
            )

            # Should have no prev_record
            self.assertFalse(result["prev_record"])
            # Should have next_record
            self.assertEqual(
                result["next_record"], f"/website/partner/{self.partner_ids[1]}"
            )

    def test_record_at_end_of_history_returns_only_prev_url(self):
        """Should return False for next_record when at end of history."""
        # Set up history with record at end
        self.mock_request.session["product_history"] = [
            self.partner_ids[0],
            self.partner_ids[1],
            self.partner_ids[2],  # Current record (last)
        ]

        with patch.object(search_module, "request", self.mock_request):
            values = {}
            result = change_previous_next_record_url(
                values=values,
                model_instance=self.partners[2],
                url="/website/partner",
                history_name="product_history",
            )

            # Should have prev_record
            self.assertEqual(
                result["prev_record"], f"/website/partner/{self.partner_ids[1]}"
            )
            # Should have no next_record
            self.assertFalse(result["next_record"])

    def test_record_not_in_history_returns_unchanged_values(self):
        """Should return values unchanged when record ID not in history."""
        # Set up history without current record
        self.mock_request.session["product_history"] = [
            self.partner_ids[0],
            self.partner_ids[1],
        ]

        with patch.object(search_module, "request", self.mock_request):
            values = {"existing_key": "existing_value"}
            result = change_previous_next_record_url(
                values=values,
                model_instance=self.partners[2],  # Not in history
                url="/website/partner",
                history_name="product_history",
            )

            # Should return original values without modifications
            self.assertEqual(result, {"existing_key": "existing_value"})
            self.assertNotIn("prev_record", result)
            self.assertNotIn("next_record", result)

    def test_empty_history_returns_unchanged_values(self):
        """Should return values unchanged when history is empty."""
        # Set up empty history
        self.mock_request.session["product_history"] = []

        with patch.object(search_module, "request", self.mock_request):
            values = {"test": "value"}
            result = change_previous_next_record_url(
                values=values,
                model_instance=self.partners[0],
                url="/website/partner",
                history_name="product_history",
            )

            # Should return original values
            self.assertEqual(result, {"test": "value"})
            self.assertNotIn("prev_record", result)
            self.assertNotIn("next_record", result)

    def test_history_not_in_session_returns_unchanged_values(self):
        """Should return values unchanged when history key not in session."""
        # No history in session at all
        self.mock_request.session = {}

        with patch.object(search_module, "request", self.mock_request):
            values = {"test": "value"}
            result = change_previous_next_record_url(
                values=values,
                model_instance=self.partners[0],
                url="/website/partner",
                history_name="nonexistent_history",
            )

            # Should return original values
            self.assertEqual(result, {"test": "value"})
            self.assertNotIn("prev_record", result)
            self.assertNotIn("next_record", result)

    def test_single_record_in_history_returns_both_false(self):
        """Should return False for both prev and next when history has single record."""
        # Set up history with single record
        self.mock_request.session["product_history"] = [self.partner_ids[0]]

        with patch.object(search_module, "request", self.mock_request):
            values = {}
            result = change_previous_next_record_url(
                values=values,
                model_instance=self.partners[0],
                url="/website/partner",
                history_name="product_history",
            )

            # Should have no prev or next
            self.assertFalse(result["prev_record"])
            self.assertFalse(result["next_record"])

    def test_two_records_in_history_first_record(self):
        """Should handle first record correctly in two-record history."""
        # Set up history with two records
        self.mock_request.session["product_history"] = [
            self.partner_ids[0],  # Current
            self.partner_ids[1],
        ]

        with patch.object(search_module, "request", self.mock_request):
            values = {}
            result = change_previous_next_record_url(
                values=values,
                model_instance=self.partners[0],
                url="/website/partner",
                history_name="product_history",
            )

            # Should have no prev, only next
            self.assertFalse(result["prev_record"])
            self.assertEqual(
                result["next_record"], f"/website/partner/{self.partner_ids[1]}"
            )

    def test_two_records_in_history_second_record(self):
        """Should handle second record correctly in two-record history."""
        # Set up history with two records
        self.mock_request.session["product_history"] = [
            self.partner_ids[0],
            self.partner_ids[1],  # Current
        ]

        with patch.object(search_module, "request", self.mock_request):
            values = {}
            result = change_previous_next_record_url(
                values=values,
                model_instance=self.partners[1],
                url="/website/partner",
                history_name="product_history",
            )

            # Should have prev, no next
            self.assertEqual(
                result["prev_record"], f"/website/partner/{self.partner_ids[0]}"
            )
            self.assertFalse(result["next_record"])

    def test_url_formatting_with_trailing_slash(self):
        """Should handle URL with trailing slash correctly."""
        self.mock_request.session["product_history"] = [
            self.partner_ids[0],
            self.partner_ids[1],  # Current
            self.partner_ids[2],
        ]

        with patch.object(search_module, "request", self.mock_request):
            values = {}
            result = change_previous_next_record_url(
                values=values,
                model_instance=self.partners[1],
                url="/website/partner/",  # With trailing slash
                history_name="product_history",
            )

            # URLs should be formatted correctly
            self.assertEqual(
                result["prev_record"],
                f"/website/partner//{self.partner_ids[0]}",  # Double slash
            )
            self.assertEqual(
                result["next_record"],
                f"/website/partner//{self.partner_ids[2]}",  # Double slash
            )

    def test_url_formatting_without_leading_slash(self):
        """Should handle URL without leading slash correctly."""
        self.mock_request.session["product_history"] = [
            self.partner_ids[0],
            self.partner_ids[1],  # Current
            self.partner_ids[2],
        ]

        with patch.object(search_module, "request", self.mock_request):
            values = {}
            result = change_previous_next_record_url(
                values=values,
                model_instance=self.partners[1],
                url="website/partner",  # No leading slash
                history_name="product_history",
            )

            # URLs should be formatted correctly
            self.assertEqual(
                result["prev_record"], f"website/partner/{self.partner_ids[0]}"
            )
            self.assertEqual(
                result["next_record"], f"website/partner/{self.partner_ids[2]}"
            )

    def test_preserves_existing_values(self):
        """Should preserve existing keys in values dict."""
        self.mock_request.session["product_history"] = [
            self.partner_ids[0],
            self.partner_ids[1],  # Current
            self.partner_ids[2],
        ]

        with patch.object(search_module, "request", self.mock_request):
            values = {
                "existing_key": "existing_value",
                "another_key": 123,
                "prev_record": "will_be_overwritten",
            }
            result = change_previous_next_record_url(
                values=values,
                model_instance=self.partners[1],
                url="/website/partner",
                history_name="product_history",
            )

            # Should preserve existing keys
            self.assertEqual(result["existing_key"], "existing_value")
            self.assertEqual(result["another_key"], 123)
            # Should overwrite prev_record
            self.assertEqual(
                result["prev_record"], f"/website/partner/{self.partner_ids[0]}"
            )

    def test_modifies_values_dict_in_place(self):
        """Should modify the values dict in place and return it."""
        self.mock_request.session["product_history"] = [
            self.partner_ids[0],
            self.partner_ids[1],  # Current
        ]

        with patch.object(search_module, "request", self.mock_request):
            values = {"test": "value"}
            result = change_previous_next_record_url(
                values=values,
                model_instance=self.partners[1],
                url="/website/partner",
                history_name="product_history",
            )

            # Should be the same dict object
            self.assertIs(result, values)
            # Both should have the new keys
            self.assertIn("prev_record", values)
            self.assertIn("next_record", values)

    def test_different_history_names_are_independent(self):
        """Should handle different history names independently."""
        # Set up two different histories
        self.mock_request.session["product_history"] = [
            self.partner_ids[0],
            self.partner_ids[1],
        ]
        self.mock_request.session["order_history"] = [
            self.partner_ids[2],
            self.partner_ids[3],
        ]

        with patch.object(search_module, "request", self.mock_request):
            # Test with product_history
            values1 = {}
            result1 = change_previous_next_record_url(
                values=values1,
                model_instance=self.partners[1],
                url="/website/product",
                history_name="product_history",
            )

            # Test with order_history
            values2 = {}
            result2 = change_previous_next_record_url(
                values=values2,
                model_instance=self.partners[3],
                url="/website/order",
                history_name="order_history",
            )

            # Each should use its own history
            self.assertEqual(
                result1["prev_record"], f"/website/product/{self.partner_ids[0]}"
            )
            self.assertEqual(
                result2["prev_record"], f"/website/order/{self.partner_ids[2]}"
            )

    def test_large_history_list(self):
        """Should handle large history lists efficiently."""
        # Create large history
        large_history = list(range(1, 101))  # 100 items
        target_index = 50
        large_history[target_index]

        self.mock_request.session["product_history"] = large_history

        # Create a partner with the target ID
        partner = self.env["res.partner"].create({"name": "Large History Partner"})
        # Temporarily override the ID in history with actual partner ID
        large_history[target_index] = partner.id
        self.mock_request.session["product_history"] = large_history

        with patch.object(search_module, "request", self.mock_request):
            values = {}
            result = change_previous_next_record_url(
                values=values,
                model_instance=partner,
                url="/website/partner",
                history_name="product_history",
            )

            # Should have both prev and next
            self.assertTrue(result["prev_record"])
            self.assertTrue(result["next_record"])
            # Should use adjacent IDs
            self.assertEqual(
                result["prev_record"],
                f"/website/partner/{large_history[target_index - 1]}",
            )
            self.assertEqual(
                result["next_record"],
                f"/website/partner/{large_history[target_index + 1]}",
            )

    def test_duplicate_ids_in_history_uses_first_occurrence(self):
        """Should use first occurrence when record ID appears multiple times in history."""
        # Set up history with duplicate IDs
        self.mock_request.session["product_history"] = [
            self.partner_ids[0],
            self.partner_ids[1],  # First occurrence (index 1)
            self.partner_ids[2],
            self.partner_ids[1],  # Duplicate (index 3)
            self.partner_ids[3],
        ]

        with patch.object(search_module, "request", self.mock_request):
            values = {}
            result = change_previous_next_record_url(
                values=values,
                model_instance=self.partners[1],  # ID appears at indices 1 and 3
                url="/website/partner",
                history_name="product_history",
            )

            # Should use first occurrence (index 1)
            self.assertEqual(
                result["prev_record"],
                f"/website/partner/{self.partner_ids[0]}",  # index 0
            )
            self.assertEqual(
                result["next_record"],
                f"/website/partner/{self.partner_ids[2]}",  # index 2
            )
