# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

"""Test cases for add_many_x_field_searchbar_filters method."""

from unittest.mock import Mock, patch

from odoo import _
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase

from ..controllers.portal import CommonPortalController


class TestAddManyXFieldSearchbarFilters(TransactionCase):
    """Test cases for the add_many_x_field_searchbar_filters method."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_model = Mock()
        self.mock_env = Mock()
        self.mock_field = Mock()

    def test_returns_empty_dict_when_field_not_in_model(self):
        """Should return empty dict when field is not in model fields."""
        self.mock_model._fields = {}

        result = CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "nonexistent_field"
        )

        self.assertEqual(result, {})

    def test_returns_empty_dict_when_field_type_not_supported(self):
        """Should return empty dict when field type is not supported."""
        self.mock_field.type = "char"  # Unsupported type
        self.mock_model._fields = {"test_field": self.mock_field}

        result = CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "test_field", env=self.mock_env
        )

        self.assertEqual(result, {})

    def test_handles_selection_field_type(self):
        """Should handle selection field type correctly."""
        self.mock_field.type = "selection"
        self.mock_field.string = "Test Selection"
        self.mock_field.selection = [("option1", "Option 1"), ("option2", "Option 2")]
        self.mock_model._fields = {"test_field": self.mock_field}

        result = CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "test_field", env=self.mock_env
        )

        # Should create divider and header
        self.assertIn("test_field_divider", result)
        self.assertIn("test_field_header", result)

        # Should create filters for each selection option
        self.assertIn("test_field_option1", result)
        self.assertIn("test_field_option2", result)

        # Verify selection filter structure
        option1_filter = result["test_field_option1"]
        self.assertEqual(option1_filter["label"], _("Option 1"))
        self.assertEqual(option1_filter["domain"], [("test_field", "in", ["option1"])])
        self.assertEqual(option1_filter["parent"], "test_field_header")

    def test_handles_many2one_field_with_search_read(self):
        """Should handle many2one field using search_read correctly."""
        # Setup field
        self.mock_field.type = "many2one"
        self.mock_field.string = "Partner"
        self.mock_field.comodel_name = "res.partner"
        self.mock_model._fields = {"partner_id": self.mock_field}

        # Setup mock environment and model
        mock_partner_model = Mock()
        mock_partner_model.search_read.return_value = [
            {"id": 1, "display_name": "Partner 1"},
            {"id": 2, "display_name": "Partner 2"},
        ]
        self.mock_env.__getitem__ = Mock(return_value=mock_partner_model)

        result = CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "partner_id", env=self.mock_env
        )

        # Verify search_read was called with correct parameters
        mock_partner_model.search_read.assert_called_once_with(
            [], fields=["id", "display_name"], limit=5, order="id desc"
        )

        # Should create basic structure
        self.assertIn("partner_id_divider", result)
        self.assertIn("partner_id_header", result)

        # Should create filters for each record
        self.assertIn("partner_id_1", result)
        self.assertIn("partner_id_2", result)

        # Verify filter structure
        partner1_filter = result["partner_id_1"]
        self.assertEqual(partner1_filter["label"], _("Partner 1"))
        self.assertEqual(partner1_filter["domain"], [("partner_id", "in", [1])])
        self.assertEqual(partner1_filter["parent"], "partner_id_header")

    def test_handles_many2many_field_with_search_read(self):
        """Should handle many2many field using search_read correctly."""
        # Setup field
        self.mock_field.type = "many2many"
        self.mock_field.string = "Tags"
        self.mock_field.comodel_name = "project.tags"
        self.mock_model._fields = {"tag_ids": self.mock_field}

        # Setup mock environment and model
        mock_tag_model = Mock()
        mock_tag_model.search_read.return_value = [
            {"id": 10, "display_name": "Important"},
            {"id": 11, "display_name": "Urgent"},
        ]
        self.mock_env.__getitem__ = Mock(return_value=mock_tag_model)

        result = CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "tag_ids", env=self.mock_env
        )

        # Verify search_read was called
        mock_tag_model.search_read.assert_called_once_with(
            [], fields=["id", "display_name"], limit=5, order="id desc"
        )

        # Should create filters for each tag
        self.assertIn("tag_ids_10", result)
        self.assertIn("tag_ids_11", result)

    def test_handles_one2many_field_with_search_read(self):
        """Should handle one2many field using search_read correctly."""
        # Setup field
        self.mock_field.type = "one2many"
        self.mock_field.string = "Lines"
        self.mock_field.comodel_name = "project.task.line"
        self.mock_model._fields = {"line_ids": self.mock_field}

        # Setup mock environment and model
        mock_line_model = Mock()
        mock_line_model.search_read.return_value = [
            {"id": 100, "display_name": "Line 1"},
        ]
        self.mock_env.__getitem__ = Mock(return_value=mock_line_model)

        result = CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "line_ids", env=self.mock_env
        )

        # Verify search_read was called
        mock_line_model.search_read.assert_called_once_with(
            [], fields=["id", "display_name"], limit=5, order="id desc"
        )

        # Should create filter for the line
        self.assertIn("line_ids_100", result)

    def test_custom_limit_parameter(self):
        """Should respect custom limit parameter in search_read."""
        # Setup field
        self.mock_field.type = "many2one"
        self.mock_field.string = "Partner"
        self.mock_field.comodel_name = "res.partner"
        self.mock_model._fields = {"partner_id": self.mock_field}

        # Setup mock environment and model
        mock_partner_model = Mock()
        mock_partner_model.search_read.return_value = []
        self.mock_env.__getitem__ = Mock(return_value=mock_partner_model)

        CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "partner_id", limit=10, env=self.mock_env
        )

        # Verify search_read was called with custom limit
        mock_partner_model.search_read.assert_called_once_with(
            [], fields=["id", "display_name"], limit=10, order="id desc"
        )

    def test_custom_order_by_parameter(self):
        """Should respect custom order_by parameter in search_read."""
        # Setup field
        self.mock_field.type = "many2one"
        self.mock_field.string = "Partner"
        self.mock_field.comodel_name = "res.partner"
        self.mock_model._fields = {"partner_id": self.mock_field}

        # Setup mock environment and model
        mock_partner_model = Mock()
        mock_partner_model.search_read.return_value = []
        self.mock_env.__getitem__ = Mock(return_value=mock_partner_model)

        CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "partner_id", order_by="name asc", env=self.mock_env
        )

        # Verify search_read was called with custom order
        mock_partner_model.search_read.assert_called_once_with(
            [], fields=["id", "display_name"], limit=5, order="name asc"
        )

    def test_custom_sequence_parameter(self):
        """Should respect custom sequence parameter."""
        self.mock_field.type = "selection"
        self.mock_field.string = "Status"
        self.mock_field.selection = [("draft", "Draft")]
        self.mock_model._fields = {"state": self.mock_field}

        result = CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "state", sequence=10, env=self.mock_env
        )

        # Check sequences start from custom value
        self.assertEqual(result["state_divider"]["sequence"], 11)
        self.assertEqual(result["state_header"]["sequence"], 12)
        self.assertEqual(result["state_draft"]["sequence"], 13)

    def test_uses_provided_env_parameter(self):
        """Should use provided env parameter instead of request.env."""
        # Setup field
        self.mock_field.type = "many2one"
        self.mock_field.string = "Partner"
        self.mock_field.comodel_name = "res.partner"
        self.mock_model._fields = {"partner_id": self.mock_field}

        # Setup custom environment
        custom_env = Mock()
        mock_partner_model = Mock()
        mock_partner_model.search_read.return_value = [
            {"id": 1, "display_name": "Custom Partner"},
        ]
        custom_env.__getitem__ = Mock(return_value=mock_partner_model)

        result = CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "partner_id", env=custom_env
        )

        # Verify custom env was used
        custom_env.__getitem__.assert_called_with("res.partner")
        mock_partner_model.search_read.assert_called_once()

        # Should create filter with custom data
        self.assertIn("partner_id_1", result)
        self.assertEqual(result["partner_id_1"]["label"], _("Custom Partner"))

    def test_handles_access_error_gracefully(self):
        """Should handle AccessError gracefully when search_read fails."""
        # Setup field
        self.mock_field.type = "many2one"
        self.mock_field.string = "Partner"
        self.mock_field.comodel_name = "res.partner"
        self.mock_model._fields = {"partner_id": self.mock_field}

        # Setup mock environment to raise AccessError
        mock_partner_model = Mock()
        mock_partner_model.search_read.side_effect = AccessError("Access denied")
        self.mock_env.__getitem__ = Mock(return_value=mock_partner_model)

        with patch(
            "odoo.addons.website_common.controllers.portal._logger"
        ) as mock_logger:
            result = CommonPortalController.add_many_x_field_searchbar_filters(
                self.mock_model, "partner_id", env=self.mock_env
            )

        # Should return empty dict when access error occurs
        self.assertEqual(result, {})

        # Should log the exception
        mock_logger.exception.assert_called_once()

    def test_handles_general_exception_gracefully(self):
        """Should handle general exceptions gracefully when search_read fails."""
        # Setup field
        self.mock_field.type = "many2one"
        self.mock_field.string = "Partner"
        self.mock_field.comodel_name = "res.partner"
        self.mock_model._fields = {"partner_id": self.mock_field}

        # Setup mock environment to raise general exception
        mock_partner_model = Mock()
        mock_partner_model.search_read.side_effect = Exception("Database error")
        self.mock_env.__getitem__ = Mock(return_value=mock_partner_model)

        with patch(
            "odoo.addons.website_common.controllers.portal._logger"
        ) as mock_logger:
            result = CommonPortalController.add_many_x_field_searchbar_filters(
                self.mock_model, "partner_id", env=self.mock_env
            )

        # Should return empty dict when exception occurs
        self.assertEqual(result, {})

        # Should log the exception with exc_info=True
        mock_logger.exception.assert_called_once()
        call_args = mock_logger.exception.call_args
        self.assertTrue(call_args[1]["exc_info"])

    def test_handles_empty_comodel_name(self):
        """Should handle fields with empty comodel_name gracefully."""
        # Setup field with no comodel_name
        self.mock_field.type = "many2one"
        self.mock_field.string = "Partner"
        self.mock_field.comodel_name = None
        self.mock_model._fields = {"partner_id": self.mock_field}

        result = CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "partner_id", env=self.mock_env
        )

        # Should return empty dict when no comodel_name
        self.assertEqual(result, {})

    def test_returns_empty_dict_when_no_records_found(self):
        """Should return empty dict when search_read returns no records."""
        # Setup field
        self.mock_field.type = "many2one"
        self.mock_field.string = "Partner"
        self.mock_field.comodel_name = "res.partner"
        self.mock_model._fields = {"partner_id": self.mock_field}

        # Setup mock environment to return empty list
        mock_partner_model = Mock()
        mock_partner_model.search_read.return_value = []
        self.mock_env.__getitem__ = Mock(return_value=mock_partner_model)

        result = CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "partner_id", env=self.mock_env
        )

        # Should return empty dict when no records
        self.assertEqual(result, {})

    def test_divider_and_header_structure(self):
        """Should create proper divider and header structure."""
        self.mock_field.type = "selection"
        self.mock_field.string = "Priority"
        self.mock_field.selection = [("high", "High Priority")]
        self.mock_model._fields = {"priority": self.mock_field}

        result = CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "priority", sequence=5, env=self.mock_env
        )

        # Verify divider structure
        divider = result["priority_divider"]
        self.assertEqual(divider["label"], _("Priority Start"))
        self.assertEqual(divider["domain"], [])
        self.assertEqual(divider["sequence"], 6)
        self.assertEqual(divider["type"], "divider")

        # Verify header structure
        header = result["priority_header"]
        self.assertEqual(header["label"], "Priority")
        self.assertEqual(header["domain"], [])
        self.assertEqual(header["sequence"], 7)
        self.assertEqual(header["type"], "header")
        self.assertEqual(header["items"], {})

    def test_filter_domain_structure(self):
        """Should create proper domain structure for filters."""
        # Setup field
        self.mock_field.type = "many2one"
        self.mock_field.string = "User"
        self.mock_field.comodel_name = "res.users"
        self.mock_model._fields = {"user_id": self.mock_field}

        # Setup mock environment and model
        mock_user_model = Mock()
        mock_user_model.search_read.return_value = [
            {"id": 42, "display_name": "John Doe"},
        ]
        self.mock_env.__getitem__ = Mock(return_value=mock_user_model)

        result = CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "user_id", env=self.mock_env
        )

        # Verify filter domain structure
        user_filter = result["user_id_42"]
        self.assertEqual(user_filter["label"], _("John Doe"))
        self.assertEqual(user_filter["domain"], [("user_id", "in", [42])])
        self.assertEqual(user_filter["sequence"], 4)
        self.assertEqual(user_filter["parent"], "user_id_header")

    def test_sequence_increments_correctly(self):
        """Should increment sequences correctly for multiple filters."""
        self.mock_field.type = "selection"
        self.mock_field.string = "State"
        self.mock_field.selection = [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
        ]
        self.mock_model._fields = {"state": self.mock_field}

        result = CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "state", sequence=1, env=self.mock_env
        )

        # Check sequence progression
        self.assertEqual(result["state_divider"]["sequence"], 2)
        self.assertEqual(result["state_header"]["sequence"], 3)
        self.assertEqual(result["state_draft"]["sequence"], 4)
        self.assertEqual(result["state_confirmed"]["sequence"], 5)
        self.assertEqual(result["state_done"]["sequence"], 6)

    def test_search_read_called_with_correct_fields(self):
        """Should call search_read with correct fields parameter."""
        # Setup field
        self.mock_field.type = "many2one"
        self.mock_field.string = "Category"
        self.mock_field.comodel_name = "product.category"
        self.mock_model._fields = {"category_id": self.mock_field}

        # Setup mock environment and model
        mock_category_model = Mock()
        mock_category_model.search_read.return_value = []
        self.mock_env.__getitem__ = Mock(return_value=mock_category_model)

        CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "category_id", env=self.mock_env
        )

        # Verify search_read was called with exactly the fields we need
        mock_category_model.search_read.assert_called_once_with(
            [], fields=["id", "display_name"], limit=5, order="id desc"
        )

    def test_record_id_conversion_to_string(self):
        """Should convert record IDs to strings in filter keys."""
        self.mock_field.type = "selection"
        self.mock_field.string = "Type"
        self.mock_field.selection = [(123, "Numeric ID")]  # Numeric ID
        self.mock_model._fields = {"type_id": self.mock_field}

        result = CommonPortalController.add_many_x_field_searchbar_filters(
            self.mock_model, "type_id", env=self.mock_env
        )

        # Should convert numeric ID to string in filter key
        self.assertIn("type_id_123", result)

        # But domain should maintain original ID type
        filter_config = result["type_id_123"]
        self.assertEqual(filter_config["domain"], [("type_id", "in", [123])])
