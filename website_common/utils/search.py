# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

import logging
from operator import itemgetter

from odoo import _, fields, models
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.api import Environment
from odoo.http import request
from odoo.osv.expression import AND, OR
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import groupby as groupbyelem

_logger = logging.getLogger(__name__)

DEFAULT_SORTBY = "name"
DEFAULT_FILTERBY = "all"


def change_previous_next_record_url(
    values: dict, model_instance: models.Model, url: str, history_name: str
) -> dict:
    """
    Generate previous and next record URLs based on navigation history.

    This function retrieves the navigation history from the session and determines
    the current record's position. It then constructs URLs for navigating to the
    previous and next records in the history list, storing them in the values dictionary.

    Args:
        values (dict): Dictionary to store the previous and next record URLs.
        model_instance (models.Model): The current model instance whose ID is used to find
            its position in the history.
        url (str): Base URL path to append the record ID to (e.g., '/website/product').
        history_name (str): The key name used to retrieve the history list from the session.

    Returns:
        dict: The updated values dictionary containing:
            - 'prev_record': URL string to the previous record, or False if at the beginning.
            - 'next_record': URL string to the next record, or False if at the end.

    Raises:
        None: Returns the original values dict unchanged if the current record ID
            is not found in the history.
    """
    history = request.session.get(history_name, [])
    try:
        current_record_index = history.index(model_instance.id)
    except ValueError:
        return values

    total_records = len(history)
    record_url = "%s/%s"

    values["prev_record"] = current_record_index != 0 and record_url % (
        url,
        history[current_record_index - 1],
    )
    values["next_record"] = current_record_index < total_records - 1 and record_url % (
        url,
        history[current_record_index + 1],
    )
    return values


def model_instance_stage_name(
    model_instance: models.Model, field_name: str, env: Environment
) -> tuple:
    """
    Get the stage name and value for a model instance field.

    This function extracts the value and display name of a specified field from a model instance,
    handling different field types appropriately (Selection, Many2one, Date, Datetime, Boolean,
    Many2many, One2many, etc.).

    Args:
        model_instance (models.Model): The Odoo model instance to extract the field value from.
            Must be a singleton record (single instance).
        field_name (str): The name of the field to retrieve the value from.
        env (Environment): The Odoo environment object used for context and translations.

    Returns:
        tuple: A tuple containing two elements:
            - The first element is the field value in a format suitable for identification/filtering:
                * For Selection fields: the selection key
                * For Many2one fields: the record ID
                * For Date/Datetime fields: the formatted date string
                * For Boolean fields: 'yes' or 'no'
                * For Many2many/One2many fields: comma-separated IDs
                * For other types: the raw value
                * "false" if field doesn't exist or has no value
            - The second element is the human-readable display name:
                * For Selection fields: the translated selection label
                * For Many2one fields: the record name
                * For Date/Datetime fields: the formatted date string
                * For Boolean fields: translated 'Yes' or 'No'
                * For Many2many/One2many fields: comma-separated record names
                * For other types: the raw value
                * The field name if field doesn't exist
                * Translated 'Not assigned' if field has no value

    Raises:
        ValueError: If model_instance is not a singleton (contains multiple records).

    Example:
        >>> stage_id, stage_name = model_instance_stage_name(project, 'stage_id', env)
        >>> # Returns: (5, 'In Progress')
    """
    model_instance.ensure_one()
    field = model_instance._fields.get(field_name, None)
    if field is None:
        return "false", field_name
    value = model_instance[field_name]
    # Boolean False is a valid value, not "unassigned"
    if not value and not isinstance(field, fields.Boolean):
        return "false", _("Not assigned")
    if isinstance(field, fields.Selection):
        selection = dict(field._description_selection(env))
        return value, selection.get(value, value)
    elif isinstance(field, fields.Many2one):
        if not value:
            return "false", _("Not assigned")
        return value.id, value.name
    elif isinstance(field, (fields.Date, fields.Datetime)):
        formatted_value = (
            value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            if field.type == "datetime"
            else value.strftime(DEFAULT_SERVER_DATE_FORMAT)
        )
        return formatted_value, formatted_value
    elif isinstance(field, fields.Boolean):
        return ("yes" if value else "no", _("Yes") if value else _("No"))
    elif isinstance(field, (fields.Many2many, fields.One2many)):
        # Ensure prefetch to avoid N+1 queries
        ids_list = value.ids  # Already loaded, no query
        names_list = value.mapped("name")  # Single query for all names
        return (
            ",".join(str(record_id) for record_id in ids_list),
            ", ".join(names_list),
        )
    else:
        return value, value


class SearchBar:
    def __init__(self) -> None:
        """
        Initialize the search configuration with default searchbar options.

        This constructor sets up various search-related dictionaries including sorting options,
        input fields, grouping options, filtering options, and pagination settings.

        Attributes:
            searchbar_sortings (dict): Dictionary containing sorting options with labels and order fields.
                Each key maps to a dict with 'label' and 'order' keys.
            searchbar_inputs (dict): Dictionary containing search input options with labels and input types.
                Each key maps to a dict with 'label' and 'input' keys.
            searchbar_groupby (dict): Dictionary containing grouping options with labels and input types.
                Each key maps to a dict with 'label' and 'input' keys.
            searchbar_filterby (dict): Dictionary containing filter options with labels and domain criteria.
                Each key maps to a dict with 'label' and 'domain' keys.
            group_by_mapping (dict): Empty dictionary for mapping grouping configurations.
            search_by_mapping (dict): Dictionary mapping tuples of (input_type, field) to actual field names.
            searchbar_listings (dict): Dictionary containing pagination options with element counts.
                Each key (page size) maps to a dict with 'input', 'label', and 'order' keys.
        """
        self.searchbar_sortings = {
            "name": {"label": _("Name"), "order": "name"},
        }
        self.searchbar_inputs = {
            "all": {"label": _("Search in all"), "input": "all"},
            "name": {"label": _("Search in name"), "input": "name"},
        }
        self.searchbar_groupby = {
            "none": {"label": _("None"), "input": "none"},
        }
        self.searchbar_filterby = {
            "all": {"label": _("All"), "domain": []},
        }
        self.group_by_mapping = {}
        self.search_by_mapping = {("all", "name"): "name"}
        self.searchbar_listings = {
            10: {"input": "10", "label": _("10 elements"), "order": 10},
        }

    def add_filterby(self, filterby) -> None:
        """
        Adds a new filter to the search bar filters.

        Args:
            filterby (dict): A dictionary containing the new filter(s) to be added.
        """
        self.searchbar_filterby.update(filterby)

    def add_groupby(self, groupby) -> None:
        """
        Adds new grouping options to the search bar.

        Args:
            groupby (dict): A dictionary containing the new grouping options.
        """
        self.searchbar_groupby.update(groupby)

    def add_inputs(self, inputs) -> None:
        """
        Adds new input options to the search bar.

        Args:
            inputs (dict): A dictionary containing the new input options.
        """
        self.searchbar_inputs.update(inputs)

    def add_sortings(self, sortings) -> None:
        """
        Adds new sorting options to the search bar.

        Args:
            sortings (dict): A dictionary containing the new sorting options.
        """
        self.searchbar_sortings.update(sortings)

    def add_listings(self, listings) -> None:
        """Add listing options to the searchbar configuration."""
        self.searchbar_listings.update(listings)

    def get_search_domain(self, search_in: str, search: str) -> list:
        """
        Gets the search domain based on the provided parameters.

        Args:
            search_in (str): The field in which to perform the search.
            search (str): The search term.

        Returns:
            list: A list representing the search domain.
        """
        search_domain = []
        for search_in_option, search_field in self.search_by_mapping.items():
            if search_in in search_in_option:
                search_domain = OR(
                    [
                        search_domain,
                        [(search_field, "ilike", search)]
                        if isinstance(search_field, str)
                        else search_field,
                    ]
                )
        return search_domain

    def set_group_by_mapping(self, group_by_mapping: dict | None = None) -> None:
        """
        Sets the mapping of grouping options.

        Args:
            group_by_mapping (dict): A dictionary containing the grouping options.
        """
        if group_by_mapping:
            self.group_by_mapping = group_by_mapping

    def prepare_searchbar_values(
        self,
        model: str,
        values: dict,
        url: str,
        ipp: int = 80,
        domain: list | None = None,
        page: int = 1,
        sortby=None,
        filterby=None,
        search=None,
        search_in="all",
        groupby=None,
        **kwargs,
    ) -> dict:
        """
        Prepares the searchbar values for the portal.

        Args:
            model (str): The Odoo model name. SECURITY: Caller MUST validate this
                 parameter if it comes from user input to prevent unauthorized access.
            values (dict): A dictionary with the current portal values.
            url (str): The base URL for pagination.
            ipp (int, optional): Items per page. Default is 80.
            domain (list, optional): The search domain. Default is None.
            page (int, optional): The current page number. Default is 1.
            sortby (str, optional): Field by which to sort items. Default is None.
            filterby (str, optional): Filter applied to items. Default is None.
            search (str, optional): Search term.
            search_in (str, optional): Field in which to perform the search. Default is 'all'.
            groupby (str, optional): Field by which to group items.
            **kwargs: Additional arguments.

        Returns:
            dict: A dictionary with the updated searchbar values.
        """
        try:
            items_per_page = int(ipp)
        except ValueError:
            _logger.warning("Invalid items_per_page value: %s, defaulting to 80", ipp)
            items_per_page = 80
        if items_per_page not in self.searchbar_listings:
            items_per_page = list(self.searchbar_listings.keys())[0]
        if domain is None:
            domain = []  # Initialize domain if None
        model_object = request.env[model]  # Get the model object
        if not sortby:
            sortby = DEFAULT_SORTBY  # Set default order if not provided
        sort_order = self.searchbar_sortings[sortby]["order"]  # Get the sort order
        # filter by default value
        if not filterby:
            filterby = DEFAULT_FILTERBY
        domain += self.searchbar_filterby[filterby]["domain"]
        groupby_field = self.group_by_mapping.get(
            groupby, None
        )  # Get the grouping field
        # Check if the grouping field exists in the model
        if groupby_field is not None and groupby_field not in model_object._fields:
            raise ValueError(
                _("The field '%s' does not exist in the targeted model", groupby_field)
            )
        order = (
            "%s, %s" % (groupby_field, sort_order) if groupby_field else sort_order
        )  # Build the sort order
        if search and search_in:
            domain = AND(
                [domain, self.get_search_domain(search_in, search)]
            )  # Add search domain if provided
        layout = kwargs.get("layout", "list")  # Get page layout, default is 'list'
        items_count = model_object.search_count(
            domain
        )  # Count items matching the domain
        pager = portal_pager(
            url=url,
            url_args={
                "sortby": sortby,
                "search_in": search_in,
                "search": search,
                "groupby": groupby,
                "listing": items_per_page,
                "layout": layout,
            },
            total=items_count,
            page=page,
            step=items_per_page,
        )  # Configure pagination
        items = model_object.search(
            domain, order=order, limit=items_per_page, offset=pager["offset"]
        )  # Search for items with specified domain and order
        group = self.group_by_mapping.get(groupby)  # Get the grouping field
        if (
            group
            and group in model_object._fields
            and isinstance(model_object._fields[group], fields.Many2one)
        ):
            # For relational fields, ensure prefetch
            items.mapped(group)  # Force prefetch
        if group:
            grouped_items = [
                model_object.concat(*g)
                for k, g in groupbyelem(items, itemgetter(group))
            ]  # Group items if a grouping field is provided
        else:
            grouped_items = (
                [items] if items else []
            )  # If no grouping, place items in a list
        values.update(
            {
                "items": items,
                "grouped_items": grouped_items,
                "pager": pager,
                "default_url": url,
                "groupby_mapping": self.group_by_mapping,
                "searchbar_sortings": self.searchbar_sortings,
                "searchbar_filters": self.searchbar_filterby,
                "search_in": search_in,
                "search": search,
                "sortby": sortby,
                "groupby": groupby or "none",
                "filterby": filterby,
                "listing": items_per_page,
                "searchbar_inputs": self.searchbar_inputs,
                "searchbar_listings": self.searchbar_listings,
                "searchbar_groupby": self.searchbar_groupby,
                "items_count": items_count,
            }
        )  # Update values with search and pagination results
        return values  # Return updated values
