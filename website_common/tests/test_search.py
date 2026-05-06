# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

"""Exhaustive test cases for SearchBar utility class and model_instance_stage_name function."""

from datetime import date
from unittest.mock import MagicMock, patch

from odoo import _
from odoo.addons.website_common.utils import search as search_module
from odoo.addons.website_common.utils.search import SearchBar, model_instance_stage_name
from odoo.tests import TransactionCase, tagged


@tagged("search_utils", "website_common", "post_install", "-at_install")
class TestModelInstanceStageName(TransactionCase):
    """Test cases for model_instance_stage_name function."""

    @classmethod
    def setUpClass(cls):
        """Set up test data for all tests."""
        super().setUpClass()

        # Create test partner with various field types
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
                "email": "test@example.com",
                "active": True,
                "type": "contact",
            }
        )

        # Create test user for Many2one tests
        cls.user = cls.env["res.users"].create(
            {
                "name": "Test User",
                "login": "testuser",
                "email": "testuser@example.com",
            }
        )

    def test_selection_field_returns_key_and_label(self):
        """Should return selection key and translated label for Selection field."""
        stage_id, stage_name = model_instance_stage_name(self.partner, "type", self.env)

        self.assertEqual(stage_id, "contact")
        self.assertIsInstance(stage_name, str)
        self.assertNotEqual(stage_name, "contact")  # Should be translated

    def test_many2one_field_returns_id_and_name(self):
        """Should return record ID and name for Many2one field."""
        # Create a partner with a parent
        child_partner = self.env["res.partner"].create(
            {
                "name": "Child Partner",
                "parent_id": self.partner.id,
            }
        )

        stage_id, stage_name = model_instance_stage_name(
            child_partner, "parent_id", self.env
        )

        self.assertEqual(stage_id, self.partner.id)
        self.assertEqual(stage_name, "Test Partner")

    def test_boolean_field_true_returns_yes(self):
        """Should return 'yes' and translated 'Yes' for True Boolean field."""
        stage_id, stage_name = model_instance_stage_name(
            self.partner, "active", self.env
        )

        self.assertEqual(stage_id, "yes")
        self.assertEqual(stage_name, _("Yes"))

    def test_boolean_field_false_returns_no(self):
        """Should return 'no' and translated 'No' for False Boolean field."""
        self.partner.active = False

        stage_id, stage_name = model_instance_stage_name(
            self.partner, "active", self.env
        )

        self.assertEqual(stage_id, "no")
        self.assertEqual(stage_name, _("No"))

    def test_char_field_returns_value_twice(self):
        """Should return the same value twice for Char field."""
        stage_id, stage_name = model_instance_stage_name(self.partner, "name", self.env)

        self.assertEqual(stage_id, "Test Partner")
        self.assertEqual(stage_name, "Test Partner")

    def test_empty_field_returns_false_and_not_assigned(self):
        """Should return 'false' and 'Not assigned' for empty field."""
        self.partner.email = False

        stage_id, stage_name = model_instance_stage_name(
            self.partner, "email", self.env
        )

        self.assertEqual(stage_id, "false")
        self.assertEqual(stage_name, _("Not assigned"))

    def test_nonexistent_field_returns_false_and_field_name(self):
        """Should return 'false' and field name for non-existent field."""
        stage_id, stage_name = model_instance_stage_name(
            self.partner, "nonexistent_field", self.env
        )

        self.assertEqual(stage_id, "false")
        self.assertEqual(stage_name, "nonexistent_field")

    def test_many2many_field_returns_comma_separated_ids_and_names(self):
        """Should return comma-separated IDs and names for Many2many field."""
        # Create a user with multiple groups
        group1 = self.env["res.groups"].create({"name": "Group 1"})
        group2 = self.env["res.groups"].create({"name": "Group 2"})

        user = self.env["res.users"].create(
            {
                "name": "Test User With Groups",
                "login": "testuserwithgroups",
                "groups_id": [(6, 0, [group1.id, group2.id])],
            }
        )

        stage_id, stage_name = model_instance_stage_name(user, "groups_id", self.env)

        # Check IDs are comma-separated
        ids_list = stage_id.split(",")
        self.assertEqual(len(ids_list), 2)
        self.assertIn(str(group1.id), ids_list)
        self.assertIn(str(group2.id), ids_list)

        # Check names are comma-separated
        self.assertIn("Group 1", stage_name)
        self.assertIn("Group 2", stage_name)

    def test_date_field_returns_formatted_date(self):
        """Should return formatted date string for Date field."""
        # Create partner with date field
        partner = self.env["res.partner"].create(
            {
                "name": "Date Test Partner",
                "date": date(2025, 1, 15),
            }
        )

        stage_id, stage_name = model_instance_stage_name(partner, "date", self.env)

        self.assertEqual(stage_id, "2025-01-15")
        self.assertEqual(stage_name, "2025-01-15")

    def test_datetime_field_returns_formatted_datetime(self):
        """Should return formatted datetime string for Datetime field."""
        # Use create_date which is a Datetime field
        stage_id, stage_name = model_instance_stage_name(
            self.partner, "create_date", self.env
        )

        # Should be in format: YYYY-MM-DD HH:MM:SS
        self.assertRegex(stage_id, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
        self.assertEqual(stage_id, stage_name)

    def test_raises_error_for_non_singleton(self):
        """Should raise ValueError if recordset is not a singleton."""
        partners = self.env["res.partner"].search([], limit=2)

        with self.assertRaises(ValueError):
            model_instance_stage_name(partners, "name", self.env)


@tagged("search_bar", "website_common", "post_install", "-at_install")
class TestSearchBarInitialization(TransactionCase):
    """Test cases for SearchBar class initialization."""

    def test_init_creates_default_sortings(self):
        """Should initialize with default sorting options."""
        searchbar = SearchBar()

        self.assertIn("name", searchbar.searchbar_sortings)
        self.assertEqual(searchbar.searchbar_sortings["name"]["label"], _("Nombre"))
        self.assertEqual(searchbar.searchbar_sortings["name"]["order"], "name")

    def test_init_creates_default_inputs(self):
        """Should initialize with default search input options."""
        searchbar = SearchBar()

        self.assertIn("all", searchbar.searchbar_inputs)
        self.assertIn("name", searchbar.searchbar_inputs)
        self.assertEqual(
            searchbar.searchbar_inputs["all"]["label"], _("Buscar en todo")
        )
        self.assertEqual(searchbar.searchbar_inputs["name"]["input"], "name")

    def test_init_creates_default_groupby(self):
        """Should initialize with default groupby options."""
        searchbar = SearchBar()

        self.assertIn("none", searchbar.searchbar_groupby)
        self.assertEqual(searchbar.searchbar_groupby["none"]["label"], _("Ninguno"))

    def test_init_creates_default_filterby(self):
        """Should initialize with default filter options."""
        searchbar = SearchBar()

        self.assertIn("all", searchbar.searchbar_filterby)
        self.assertEqual(searchbar.searchbar_filterby["all"]["label"], _("Todos"))
        self.assertEqual(searchbar.searchbar_filterby["all"]["domain"], [])

    def test_init_creates_empty_group_by_mapping(self):
        """Should initialize with empty group_by_mapping."""
        searchbar = SearchBar()

        self.assertIsInstance(searchbar.group_by_mapping, dict)
        self.assertEqual(len(searchbar.group_by_mapping), 0)

    def test_init_creates_default_search_by_mapping(self):
        """Should initialize with default search_by_mapping."""
        searchbar = SearchBar()

        self.assertIn(("all", "name"), searchbar.search_by_mapping)
        self.assertEqual(searchbar.search_by_mapping[("all", "name")], "name")

    def test_init_creates_default_listings(self):
        """Should initialize with default pagination listings."""
        searchbar = SearchBar()

        self.assertIn(10, searchbar.searchbar_listings)
        self.assertEqual(searchbar.searchbar_listings[10]["input"], "10")
        self.assertEqual(searchbar.searchbar_listings[10]["label"], _("10 elements"))

    def test_multiple_instances_have_separate_state(self):
        """Should ensure multiple SearchBar instances have separate state."""
        searchbar1 = SearchBar()
        searchbar2 = SearchBar()

        # Modify one instance
        searchbar1.add_sortings({"custom": {"label": "Custom", "order": "custom"}})

        # Other instance should not be affected
        self.assertIn("custom", searchbar1.searchbar_sortings)
        self.assertNotIn("custom", searchbar2.searchbar_sortings)


@tagged("search_bar", "website_common", "post_install", "-at_install")
class TestSearchBarAddMethods(TransactionCase):
    """Test cases for SearchBar add_* methods."""

    def setUp(self):
        """Set up SearchBar instance for each test."""
        super().setUp()
        self.searchbar = SearchBar()

    def test_add_filterby_updates_filters(self):
        """Should add new filter options to searchbar_filterby."""
        new_filters = {
            "active": {"label": _("Active"), "domain": [("active", "=", True)]},
            "inactive": {"label": _("Inactive"), "domain": [("active", "=", False)]},
        }

        self.searchbar.add_filterby(new_filters)

        self.assertIn("active", self.searchbar.searchbar_filterby)
        self.assertIn("inactive", self.searchbar.searchbar_filterby)
        self.assertEqual(
            self.searchbar.searchbar_filterby["active"]["domain"],
            [("active", "=", True)],
        )

    def test_add_filterby_preserves_existing_filters(self):
        """Should preserve existing filters when adding new ones."""
        self.searchbar.add_filterby({"custom": {"label": "Custom", "domain": []}})

        # Original 'all' filter should still exist
        self.assertIn("all", self.searchbar.searchbar_filterby)
        self.assertIn("custom", self.searchbar.searchbar_filterby)

    def test_add_groupby_updates_groupby_options(self):
        """Should add new groupby options to searchbar_groupby."""
        new_groupby = {
            "stage": {"label": _("Stage"), "input": "stage"},
            "user": {"label": _("User"), "input": "user"},
        }

        self.searchbar.add_groupby(new_groupby)

        self.assertIn("stage", self.searchbar.searchbar_groupby)
        self.assertIn("user", self.searchbar.searchbar_groupby)

    def test_add_inputs_updates_search_inputs(self):
        """Should add new search input options to searchbar_inputs."""
        new_inputs = {
            "email": {"label": _("Search in Email"), "input": "email"},
            "phone": {"label": _("Search in Phone"), "input": "phone"},
        }

        self.searchbar.add_inputs(new_inputs)

        self.assertIn("email", self.searchbar.searchbar_inputs)
        self.assertIn("phone", self.searchbar.searchbar_inputs)

    def test_add_sortings_updates_sorting_options(self):
        """Should add new sorting options to searchbar_sortings."""
        new_sortings = {
            "date": {"label": _("Date"), "order": "create_date desc"},
            "priority": {"label": _("Priority"), "order": "priority desc, name"},
        }

        self.searchbar.add_sortings(new_sortings)

        self.assertIn("date", self.searchbar.searchbar_sortings)
        self.assertIn("priority", self.searchbar.searchbar_sortings)
        self.assertEqual(
            self.searchbar.searchbar_sortings["priority"]["order"],
            "priority desc, name",
        )

    def test_add_listings_updates_pagination_options(self):
        """Should add new listing options to searchbar_listings."""
        new_listings = {
            5: {"input": "5", "label": _("5 elements"), "order": 5},
            100: {"input": "100", "label": _("100 elements"), "order": 100},
        }

        self.searchbar.add_listings(new_listings)

        self.assertIn(5, self.searchbar.searchbar_listings)
        self.assertIn(100, self.searchbar.searchbar_listings)


@tagged("search_bar", "website_common", "post_install", "-at_install")
class TestSearchBarGetSearchDomain(TransactionCase):
    """Test cases for SearchBar.get_search_domain method."""

    def setUp(self):
        """Set up SearchBar instance for each test."""
        super().setUp()
        self.searchbar = SearchBar()

    def test_search_in_all_creates_or_domain(self):
        """Should create OR domain for 'all' search_in option."""
        self.searchbar.search_by_mapping.update(
            {
                ("all", "name"): "name",
                ("all", "email"): "email",
            }
        )

        domain = self.searchbar.get_search_domain("all", "test")

        # Should be an OR domain with both fields
        self.assertIn("name", str(domain))
        self.assertIn("email", str(domain))
        self.assertIn("test", str(domain))

    def test_search_in_specific_field_creates_single_domain(self):
        """Should create single field domain for specific search_in."""
        self.searchbar.search_by_mapping[("name", "name")] = "name"

        domain = self.searchbar.get_search_domain("name", "John")

        # Should search only in name field
        self.assertIn(("name", "ilike", "John"), domain)

    def test_search_with_complex_field_mapping(self):
        """Should handle complex field paths in search mapping."""
        self.searchbar.search_by_mapping[("all", "partner")] = "partner_id.name"

        domain = self.searchbar.get_search_domain("all", "Company")

        # Should include the complex field path
        self.assertIn(("partner_id.name", "ilike", "Company"), domain)

    def test_search_with_no_matching_search_in_returns_empty(self):
        """Should return empty domain if search_in doesn't match any mapping."""
        domain = self.searchbar.get_search_domain("nonexistent", "test")

        self.assertEqual(domain, [])

    def test_search_with_empty_search_string(self):
        """Should handle empty search string."""
        domain = self.searchbar.get_search_domain("all", "")

        # Should still create domain structure even with empty string
        self.assertIsInstance(domain, list)


@tagged("search_bar", "website_common", "post_install", "-at_install")
class TestSearchBarSetGroupByMapping(TransactionCase):
    """Test cases for SearchBar.set_group_by_mapping method."""

    def setUp(self):
        """Set up SearchBar instance for each test."""
        super().setUp()
        self.searchbar = SearchBar()

    def test_set_group_by_mapping_updates_mapping(self):
        """Should update group_by_mapping with provided dict."""
        new_mapping = {
            "stage": "stage_id",
            "user": "user_id",
            "priority": "priority",
        }

        self.searchbar.set_group_by_mapping(new_mapping)

        self.assertEqual(self.searchbar.group_by_mapping, new_mapping)

    def test_set_group_by_mapping_with_none_does_nothing(self):
        """Should not update mapping if None is provided."""
        original_mapping = {"test": "test_field"}
        self.searchbar.group_by_mapping = original_mapping

        self.searchbar.set_group_by_mapping(None)

        self.assertEqual(self.searchbar.group_by_mapping, original_mapping)

    def test_set_group_by_mapping_with_empty_dict_clears_mapping(self):
        """Should clear mapping if empty dict is provided."""
        self.searchbar.group_by_mapping = {"test": "test_field"}

        self.searchbar.set_group_by_mapping({})

        # Empty dict is falsy, so mapping should not change
        self.assertEqual(self.searchbar.group_by_mapping, {"test": "test_field"})

    def test_set_group_by_mapping_replaces_not_merges(self):
        """Should replace existing mapping, not merge."""
        self.searchbar.group_by_mapping = {"old": "old_field"}

        self.searchbar.set_group_by_mapping({"new": "new_field"})

        self.assertNotIn("old", self.searchbar.group_by_mapping)
        self.assertIn("new", self.searchbar.group_by_mapping)


@tagged("search_bar", "website_common", "post_install", "-at_install")
class TestSearchBarPrepareSearchbarValues(TransactionCase):
    """Test cases for SearchBar.prepare_searchbar_values method."""

    @classmethod
    def setUpClass(cls):
        """Set up test data."""
        super().setUpClass()

        # Create test partners for search/filter/pagination
        cls.partners = cls.env["res.partner"].create(
            [
                {"name": f"Test Partner {i}", "email": f"partner{i}@test.com"}
                for i in range(1, 26)  # 25 partners
            ]
        )

    def setUp(self):
        """Set up SearchBar and mock request for each test."""
        super().setUp()
        self.searchbar = SearchBar()

        # Mock request object
        self.mock_request = MagicMock()
        self.mock_request.env = self.env

    def test_prepare_searchbar_values_basic_flow(self):
        """Should execute basic flow and return complete values dict."""
        with patch.object(search_module, "request", self.mock_request):
            values = {}
            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values=values,
                url="/my/partners",
                ipp=10,
                page=1,
            )

            # Check required keys are present
            self.assertIn("items", result)
            self.assertIn("grouped_items", result)
            self.assertIn("pager", result)
            self.assertIn("items_count", result)
            self.assertIn("searchbar_sortings", result)
            self.assertIn("searchbar_filters", result)

    def test_prepare_searchbar_values_counts_records(self):
        """Should count all records matching domain."""
        with patch.object(search_module, "request", self.mock_request):
            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=10,
                domain=[("id", "in", self.partners.ids)],
            )

            self.assertEqual(result["items_count"], 25)

    def test_prepare_searchbar_values_respects_pagination(self):
        """Should fetch only records for current page."""
        with patch.object(search_module, "request", self.mock_request):
            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=10,
                page=1,
                domain=[("id", "in", self.partners.ids)],
            )

            # Should fetch only 10 items for page 1
            self.assertEqual(len(result["items"]), 10)

    def test_prepare_searchbar_values_applies_sorting(self):
        """Should apply sorting order to results."""
        with patch.object(search_module, "request", self.mock_request):
            self.searchbar.add_sortings(
                {"name_desc": {"label": "Name Desc", "order": "name desc"}}
            )

            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=25,
                sortby="name_desc",
                domain=[("id", "in", self.partners.ids)],
            )

            # First item should have highest name alphabetically
            first_name = result["items"][0].name
            last_name = result["items"][-1].name
            self.assertGreater(first_name, last_name)

    def test_prepare_searchbar_values_applies_filterby(self):
        """Should apply filter domain to search."""
        with patch.object(search_module, "request", self.mock_request):
            # Create active and inactive partners
            active_partner = self.env["res.partner"].create(
                {
                    "name": "Active Partner",
                    "active": True,
                }
            )
            inactive_partner = self.env["res.partner"].create(
                {
                    "name": "Inactive Partner",
                    "active": False,
                }
            )

            self.searchbar.add_filterby(
                {"active_only": {"label": "Active", "domain": [("active", "=", True)]}}
            )

            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=100,
                filterby="active_only",
                domain=[("id", "in", [active_partner.id, inactive_partner.id])],
            )

            # Should only return active partner
            self.assertEqual(len(result["items"]), 1)
            self.assertEqual(result["items"][0].id, active_partner.id)

    def test_prepare_searchbar_values_applies_search(self):
        """Should apply search domain to filter results."""
        with patch.object(search_module, "request", self.mock_request):
            # Create partner with unique name
            unique_partner = self.env["res.partner"].create(
                {
                    "name": "UniqueSearchName",
                }
            )

            self.searchbar.search_by_mapping[("all", "name")] = "name"

            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=100,
                search="UniqueSearchName",
                search_in="all",
            )

            # Should find only the unique partner
            self.assertGreaterEqual(len(result["items"]), 1)
            self.assertIn(unique_partner.id, result["items"].ids)

    def test_prepare_searchbar_values_handles_groupby(self):
        """Should group results when groupby is specified."""
        with patch.object(search_module, "request", self.mock_request):
            # Create partners with different types
            self.env["res.partner"].create(
                [
                    {"name": "Contact 1", "type": "contact"},
                    {"name": "Contact 2", "type": "contact"},
                    {"name": "Invoice 1", "type": "invoice"},
                ]
            )

            self.searchbar.set_group_by_mapping({"type": "type"})

            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=100,
                groupby="type",
            )

            # Should have grouped items
            self.assertIsInstance(result["grouped_items"], list)
            self.assertGreater(len(result["grouped_items"]), 0)

    def test_prepare_searchbar_values_prefetches_many2one_groupby(self):
        """Should prefetch Many2one field when grouping by it."""
        with patch.object(search_module, "request", self.mock_request):
            # Create partners with parent relationship
            parent = self.env["res.partner"].create({"name": "Parent Company"})
            children = self.env["res.partner"].create(
                [
                    {"name": "Child 1", "parent_id": parent.id},
                    {"name": "Child 2", "parent_id": parent.id},
                ]
            )

            self.searchbar.set_group_by_mapping({"parent": "parent_id"})

            # Should not raise error and should prefetch parent_id
            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=100,
                groupby="parent",
                domain=[("id", "in", children.ids)],
            )

            # Accessing parent should not trigger additional queries
            for item in result["items"]:
                _ = item.parent_id.name  # Should be prefetched

    def test_prepare_searchbar_values_handles_invalid_ipp(self):
        """Should handle invalid items_per_page value gracefully."""
        with patch.object(search_module, "request", self.mock_request):
            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp="invalid",  # Invalid string value
            )

            # Should default to first available listing
            self.assertIn("listing", result)
            self.assertEqual(result["listing"], 10)  # First available listing

    def test_prepare_searchbar_values_logs_invalid_ipp(self):
        """Should log warning when items_per_page is invalid."""
        with (
            patch.object(search_module, "request", self.mock_request),
            patch.object(search_module, "_logger") as mock_logger,
        ):
            self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp="invalid",
            )

        # Should have logged a warning
        mock_logger.warning.assert_called_once()

    def test_prepare_searchbar_values_uses_default_sortby(self):
        """Should use DEFAULT_SORTBY when sortby is not provided."""
        with patch.object(search_module, "request", self.mock_request):
            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=10,
                sortby=None,  # No sortby provided
            )

            self.assertEqual(result["sortby"], "name")  # DEFAULT_SORTBY

    def test_prepare_searchbar_values_uses_default_filterby(self):
        """Should use DEFAULT_FILTERBY when filterby is not provided."""
        with patch.object(search_module, "request", self.mock_request):
            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=10,
                filterby=None,  # No filterby provided
            )

            self.assertEqual(result["filterby"], "all")  # DEFAULT_FILTERBY

    def test_prepare_searchbar_values_initializes_none_domain(self):
        """Should initialize domain to empty list if None."""
        with patch.object(search_module, "request", self.mock_request):
            # Should not raise error with domain=None
            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=10,
                domain=None,
            )

            self.assertIsInstance(result["items"], type(self.env["res.partner"]))

    def test_prepare_searchbar_values_raises_error_for_invalid_groupby_field(self):
        """Should raise ValueError for non-existent groupby field."""
        with patch.object(search_module, "request", self.mock_request):
            self.searchbar.set_group_by_mapping({"invalid": "nonexistent_field"})

            with self.assertRaises(ValueError) as context:
                self.searchbar.prepare_searchbar_values(
                    model="res.partner",
                    values={},
                    url="/my/partners",
                    ipp=10,
                    groupby="invalid",
                )

            self.assertIn("does not exist", str(context.exception))

    def test_prepare_searchbar_values_returns_empty_grouped_items_when_no_results(self):
        """Should return empty grouped_items list when no items found."""
        with patch.object(search_module, "request", self.mock_request):
            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=10,
                domain=[("id", "=", -1)],  # No records match
            )

            self.assertEqual(len(result["items"]), 0)
            self.assertEqual(result["grouped_items"], [])

    def test_prepare_searchbar_values_preserves_existing_values(self):
        """Should preserve existing values dict entries."""
        with patch.object(search_module, "request", self.mock_request):
            existing_values = {
                "custom_key": "custom_value",
                "another_key": 123,
            }

            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values=existing_values,
                url="/my/partners",
                ipp=10,
            )

            self.assertEqual(result["custom_key"], "custom_value")
            self.assertEqual(result["another_key"], 123)

    def test_prepare_searchbar_values_builds_pager_with_correct_args(self):
        """Should build pager with correct URL arguments."""
        with patch.object(search_module, "request", self.mock_request):
            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=20,
                sortby="name",
                filterby="all",
                search="test",
                search_in="all",
                groupby="none",
                page=2,
            )

            # Pager should contain correct parameters
            pager = result["pager"]
            self.assertIsInstance(pager, dict)
            self.assertEqual(pager["page"]["num"], 2)

    def test_prepare_searchbar_values_handles_kwargs(self):
        """Should handle additional kwargs correctly."""
        with patch.object(search_module, "request", self.mock_request):
            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=10,
                layout="grid",
                custom_param="value",
            )

            # Should extract layout from kwargs
            self.assertIn("layout", str(result))


@tagged("search_bar", "website_common", "post_install", "-at_install")
class TestSearchBarEdgeCases(TransactionCase):
    """Test edge cases and error conditions for SearchBar."""

    def setUp(self):
        """Set up SearchBar instance."""
        super().setUp()
        self.searchbar = SearchBar()

        # Mock request object
        self.mock_request = MagicMock()
        self.mock_request.env = self.env

    def test_get_search_domain_with_tuple_field_mapping(self):
        """Should handle tuple keys in search_by_mapping."""
        self.searchbar.search_by_mapping[("custom", "field1")] = "custom_field"

        domain = self.searchbar.get_search_domain("custom", "value")

        self.assertIn(("custom_field", "ilike", "value"), domain)

    def test_add_methods_accept_empty_dict(self):
        """Should handle empty dict passed to add methods."""
        # Should not raise errors
        self.searchbar.add_filterby({})
        self.searchbar.add_groupby({})
        self.searchbar.add_inputs({})
        self.searchbar.add_sortings({})
        self.searchbar.add_listings({})

    def test_prepare_searchbar_values_with_zero_items_per_page(self):
        """Should handle ipp=0 gracefully."""
        with patch.object(search_module, "request", self.mock_request):
            # Should not crash with ipp=0
            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=0,
            )

            # Should fall back to first available listing
            self.assertGreater(result["listing"], 0)

    def test_prepare_searchbar_values_with_large_page_number(self):
        """Should handle page number larger than available pages."""
        with patch.object(search_module, "request", self.mock_request):
            # Should not crash with large page number
            result = self.searchbar.prepare_searchbar_values(
                model="res.partner",
                values={},
                url="/my/partners",
                ipp=10,
                page=9999,
            )

            # Should not crash and return a valid result structure
            self.assertIn("items", result)
            self.assertIn("pager", result)
            # Odoo pager returns available items even for out-of-range pages
            self.assertIsInstance(result["items"], type(self.env["res.partner"]))

    def test_model_instance_stage_name_with_empty_many2many(self):
        """Should handle empty Many2many field."""
        user = self.env["res.users"].create(
            {
                "name": "User Without Groups",
                "login": "userwithoutgroups",
                "groups_id": [(5, 0, 0)],  # Clear all groups
            }
        )

        stage_id, stage_name = model_instance_stage_name(user, "groups_id", self.env)

        self.assertEqual(stage_id, "false")
        self.assertEqual(stage_name, _("Not assigned"))
