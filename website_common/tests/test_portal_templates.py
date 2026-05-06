# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

"""Test cases for portal_searchbar template."""

from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


@tagged("templates", "portal_searchbar", "portal", "website_common")
class TestPortalSearchbarTemplate(TransactionCase):
    """Test cases for the portal_searchbar template."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.template_id = "website_common.portal_searchbar"

    def test_portal_searchbar_renders_with_all_components(self):
        """Should render all searchbar components when all data is provided."""
        context = {
            "searchbar_listings": {
                "10": {"label": "10 items"},
                "25": {"label": "25 items"},
            },
            "listing": "10",
            "searchbar_sortings": {
                "date": {"label": "Date"},
                "name": {"label": "Name"},
            },
            "sortby": "date",
            "searchbar_filters": {
                "all": {"label": "All"},
                "active": {"label": "Active"},
            },
            "filterby": "all",
            "searchbar_groupby": {
                "none": {"label": "None"},
                "status": {"label": "Status"},
            },
            "groupby": "none",
            "searchbar_inputs": {
                "all": {"label": "All"},
                "name": {"input": "name", "label": "Name"},
            },
            "search_in": "all",
            "search": "",
            "default_url": "/my",
            "extra_args": {},
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b"# elements", rendered)
        self.assertIn(b"Sort By", rendered)
        self.assertIn(b"Filter By", rendered)
        self.assertIn(b"Group By", rendered)
        self.assertIn(b"Search By", rendered)
        self.assertIn(b"btn-group-portal-searchbar", rendered)

    def test_listing_dropdown_displays_correctly(self):
        """Should display listing dropdown with correct options and active state."""
        context = {
            "searchbar_listings": {
                "10": {"label": "10 items", "input": "10"},
                "25": {"label": "25 items", "input": "25"},
                "50": {"label": "50 items", "input": "50"},
            },
            "listing": "25",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b"listCountMenuButton", rendered)
        self.assertIn(b"10 items", rendered)
        self.assertIn(b"25 items", rendered)
        self.assertIn(b"50 items", rendered)

    def test_sort_by_dropdown_displays_correctly(self):
        """Should display sort by dropdown with correct options and active state."""
        context = {
            "searchbar_sortings": {
                "date": {"label": "Date"},
                "name": {"label": "Name"},
                "priority": {"label": "Priority"},
            },
            "sortby": "name",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b"sortByMenuButton", rendered)
        self.assertIn(b"Sort By", rendered)
        self.assertIn(b"Name", rendered)
        self.assertIn(b"Date", rendered)
        self.assertIn(b"Priority", rendered)

    def test_filter_by_dropdown_displays_correctly(self):
        """Should display filter by dropdown with correct options and active state."""
        context = {
            "searchbar_filters": {
                "all": {"label": "All"},
                "active": {"label": "Active"},
                "draft": {"label": "Draft"},
            },
            "filterby": "active",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b"filterByMenuButton", rendered)
        self.assertIn(b"Filter By", rendered)
        self.assertIn(b"All", rendered)
        self.assertIn(b"Active", rendered)
        self.assertIn(b"Draft", rendered)

    def test_filter_by_dropdown_handles_hierarchical_filters(self):
        """Should display hierarchical filters with headers and children correctly."""
        context = {
            "searchbar_filters": {
                "status_header": {
                    "label": "Status",
                    "type": "header",
                    "domain": [],
                    "sequence": 1,
                },
                "draft": {
                    "label": "Draft",
                    "parent": "status_header",
                    "domain": [("state", "=", "draft")],
                    "sequence": 2,
                },
                "confirmed": {
                    "label": "Confirmed",
                    "parent": "status_header",
                    "domain": [("state", "=", "confirmed")],
                    "sequence": 3,
                },
            },
            "filterby": "draft",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b"has-submenu", rendered)
        self.assertIn(b"submenu-status_header", rendered)
        self.assertIn(b"Status", rendered)
        self.assertIn(b"Draft", rendered)
        self.assertIn(b"Confirmed", rendered)

    def test_filter_by_dropdown_handles_dividers(self):
        """Should display dividers in filter dropdown correctly."""
        context = {
            "searchbar_filters": {
                "all": {"label": "All"},
                "divider1": {"type": "divider"},
                "active": {"label": "Active"},
            },
            "filterby": "all",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b"dropdown-divider", rendered)

    def test_group_by_dropdown_displays_correctly(self):
        """Should display group by dropdown with correct options and active state."""
        context = {
            "searchbar_groupby": {
                "none": {"label": "None"},
                "status": {"label": "Status"},
                "priority": {"label": "Priority"},
            },
            "groupby": "status",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b"groupByMenuButton", rendered)
        self.assertIn(b"Group By", rendered)
        self.assertIn(b"None", rendered)
        self.assertIn(b"Status", rendered)
        self.assertIn(b"Priority", rendered)

    def test_search_by_dropdown_displays_correctly(self):
        """Should display search by dropdown with search form and options."""
        context = {
            "searchbar_inputs": {
                "all": {"label": "All", "input": "all"},
                "name": {"label": "Name", "input": "name"},
                "email": {"label": "Email", "input": "email"},
            },
            "search_in": "name",
            "search": "test search",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b"searchByMenuButton", rendered)
        self.assertIn(b"Search By", rendered)
        self.assertIn(b"o_portal_soltein_search_panel", rendered)
        self.assertIn(b"test search", rendered)

    def test_handles_missing_searchbar_listings_gracefully(self):
        """Should not render listings dropdown when searchbar_listings is not provided."""
        context = {"searchbar_sortings": {"date": {"label": "Date"}}, "sortby": "date"}

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertNotIn(b"listCountMenuButton", rendered)
        self.assertNotIn(b"# elements", rendered)

    def test_handles_missing_searchbar_sortings_gracefully(self):
        """Should not render sort dropdown when searchbar_sortings is not provided."""
        context = {"searchbar_filters": {"all": {"label": "All"}}, "filterby": "all"}

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertNotIn(b"sortByMenuButton", rendered)
        self.assertNotIn(b"Sort By", rendered)

    def test_handles_missing_searchbar_filters_gracefully(self):
        """Should not render filter dropdown when searchbar_filters is not provided."""
        context = {"searchbar_sortings": {"date": {"label": "Date"}}, "sortby": "date"}

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertNotIn(b"filterByMenuButton", rendered)
        self.assertNotIn(b"Filter By", rendered)

    def test_handles_missing_searchbar_groupby_gracefully(self):
        """Should not render group by dropdown when searchbar_groupby is not provided."""
        context = {"searchbar_sortings": {"date": {"label": "Date"}}, "sortby": "date"}

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertNotIn(b"groupByMenuButton", rendered)
        self.assertNotIn(b"Group By", rendered)

    def test_handles_missing_searchbar_inputs_gracefully(self):
        """Should not render search dropdown when searchbar_inputs is not provided."""
        context = {"searchbar_sortings": {"date": {"label": "Date"}}, "sortby": "date"}

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertNotIn(b"searchByMenuButton", rendered)
        self.assertNotIn(b"Search By", rendered)

    def test_generates_correct_urls_with_keep_query(self):
        """Should generate correct URLs using keep_query for maintaining parameters."""
        context = {
            "searchbar_sortings": {
                "date": {"label": "Date"},
                "name": {"label": "Name"},
            },
            "sortby": "date",
            "default_url": "/my/tasks",
            "extra_args": {"project_id": "5"},
        }

        with patch(
            "odoo.addons.portal.controllers.portal.keep_query"
        ) as mock_keep_query:
            mock_keep_query.return_value = "sortby=name&project_id=5"

            rendered = self.env["ir.ui.view"]._render_template(
                self.template_id, context
            )

            self.assertIn(b"/my/tasks?sortby=name&project_id=5", rendered)

    def test_displays_active_filter_label_correctly(self):
        """Should display the correct active filter label in the button."""
        context = {
            "searchbar_filters": {
                "all": {"label": "All Items"},
                "active": {"label": "Active Items"},
                "draft": {"label": "Draft Items"},
            },
            "filterby": "active",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b"Active Items", rendered)

    def test_displays_active_sort_label_correctly(self):
        """Should display the correct active sort label in the button."""
        context = {
            "searchbar_sortings": {
                "date": {"label": "Creation Date"},
                "name": {"label": "Alphabetical"},
                "priority": {"label": "Priority Level"},
            },
            "sortby": "priority",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b"Priority Level", rendered)

    def test_displays_active_group_label_correctly(self):
        """Should display the correct active group label in the button."""
        context = {
            "searchbar_groupby": {
                "none": {"label": "No Grouping"},
                "status": {"label": "By Status"},
                "user": {"label": "By User"},
            },
            "groupby": "user",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b"By User", rendered)

    def test_handles_empty_filter_values_gracefully(self):
        """Should handle empty or None filter values without breaking."""
        context = {
            "searchbar_filters": {"all": {"label": "All"}},
            "filterby": None,
            "searchbar_sortings": {"date": {"label": "Date"}},
            "sortby": "",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b"Filter By", rendered)
        self.assertIn(b"Sort By", rendered)

    def test_renders_bootstrap_dropdown_structure_correctly(self):
        """Should render proper Bootstrap dropdown structure with all required attributes."""
        context = {
            "searchbar_filters": {"all": {"label": "All"}},
            "filterby": "all",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b'data-bs-toggle="dropdown"', rendered)
        self.assertIn(b'aria-expanded="false"', rendered)
        self.assertIn(b"dropdown-menu", rendered)
        self.assertIn(b"dropdown-item", rendered)

    def test_handles_complex_hierarchical_filter_structure(self):
        """Should handle complex hierarchical filters with multiple levels and mixed types."""
        context = {
            "searchbar_filters": {
                "all": {"label": "All", "type": "option"},
                "divider1": {"type": "divider"},
                "status_header": {
                    "label": "By Status",
                    "type": "header",
                    "domain": [],
                    "sequence": 2,
                },
                "draft": {
                    "label": "Draft Status",
                    "parent": "status_header",
                    "domain": [("state", "=", "draft")],
                    "sequence": 3,
                },
                "confirmed": {
                    "label": "Confirmed Status",
                    "parent": "status_header",
                    "domain": [("state", "=", "confirmed")],
                    "sequence": 4,
                },
                "divider2": {"type": "divider"},
                "priority_header": {
                    "label": "By Priority",
                    "type": "header",
                    "domain": [],
                    "sequence": 5,
                },
                "high": {
                    "label": "High Priority",
                    "parent": "priority_header",
                    "domain": [("priority", "=", "high")],
                    "sequence": 6,
                },
            },
            "filterby": "draft",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b"By Status", rendered)
        self.assertIn(b"By Priority", rendered)
        self.assertIn(b"Draft Status", rendered)
        self.assertIn(b"High Priority", rendered)
        self.assertIn(b"dropdown-divider", rendered)
        self.assertIn(b"has-submenu", rendered)

    def test_search_form_contains_proper_input_field(self):
        """Should render search form with proper input field and attributes."""
        context = {
            "searchbar_inputs": {
                "all": {"label": "All", "input": "all"},
                "name": {"label": "Name", "input": "name"},
            },
            "search_in": "name",
            "search": "my search term",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b'<input type="text"', rendered)
        self.assertIn(b'class="form-control w-100"', rendered)
        self.assertIn(b'placeholder="Search"', rendered)
        self.assertIn(b'name="search"', rendered)
        self.assertIn(b"my search term", rendered)

    def test_collapsed_submenu_expands_when_filter_active(self):
        """Should expand submenu when an item within it is the active filter."""
        context = {
            "searchbar_filters": {
                "status_header": {
                    "label": "Status",
                    "type": "header",
                    "domain": [],
                    "sequence": 1,
                },
                "active_item": {
                    "label": "Active Item",
                    "parent": "status_header",
                    "domain": [("state", "=", "active")],
                    "sequence": 2,
                },
            },
            "filterby": "active_item",
            "default_url": "/my",
        }

        rendered = self.env["ir.ui.view"]._render_template(self.template_id, context)

        self.assertIn(b"collapse submenu show", rendered)
        self.assertIn(b"active", rendered)

    def test_generates_correct_toggle_all_behavior(self):
        """Should generate correct URLs that toggle back to 'all' when same filter is clicked."""
        context = {
            "searchbar_filters": {
                "all": {"label": "All"},
                "active": {"label": "Active"},
            },
            "filterby": "active",
            "default_url": "/my",
        }

        with patch(
            "odoo.addons.portal.controllers.portal.keep_query"
        ) as mock_keep_query:
            mock_keep_query.return_value = "filterby=all"

            rendered = self.env["ir.ui.view"]._render_template(
                self.template_id, context
            )

            self.assertIn(b"filterby=all", rendered)
