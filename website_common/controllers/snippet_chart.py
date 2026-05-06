# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

import logging
from typing import Any

from odoo import _, http

_logger = logging.getLogger(__name__)


class SnippetChartController(http.Controller):
    @http.route("/snippet_chart/all", type="json", auth="public", website=True)
    def get_snippet_chart_all(
        self,
        website_id: int,
        is_published: bool = True,
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all snippet charts for a given website.

        Parameters:
        - website_id: The ID of the website to filter charts by.
        - is_published: Whether to include only published charts. Defaults to True.
        - fields: Optional list of field names to include in the response. Ensures `id` and `name` are present.

        Returns:
        - A list of dictionaries representing snippet charts matching the filters.
        """
        if fields is None:
            fields = ["id", "name"]
        else:
            fields = fields + [item for item in ["id", "name"] if item not in fields]
        snippet_chart_object = http.request.env["snippet.chart"]
        return snippet_chart_object.search_read(
            [("is_published", "=", is_published), ("website_id", "=", website_id)],
            fields=fields,
        )

    @http.route("/snippet_chart/one", type="json", auth="public", website=True)
    def get_snippet_chart_one(
        self,
        chart_id: int,
        website_id: int,
        is_published: bool = True,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve a single snippet chart for the given website.

        Parameters:
        - chart_id: The unique identifier of the chart to retrieve.
        - website_id: The website identifier used to scope the chart.
        - is_published: Filter to only include published charts. Defaults to True.
        - fields: Optional list of field names to include. Ensures `id` and `name` are included.

        Returns:
        - A dictionary with chart data if found, otherwise a default chart structure.
        """
        if fields is None:
            fields = ["id", "name"]
        else:
            fields = fields + [item for item in ["id", "name"] if item not in fields]
        chart = http.request.env["snippet.chart"].search_read(
            [
                ("id", "=", chart_id),
                ("is_published", "=", is_published),
                ("website_id", "=", website_id),
            ],
            fields=fields,
            limit=1,
        )
        return (
            chart[0]
            if chart
            else {
                "id": 0,
                "name": "",
                "subtitle": "",
                "description": "",
                "chart_type": "bar",
                "data_source_type": "internal",
                "data_source": "",
                "link_text": "",
                "link_url": "",
                "color": "blue",
            }
        )

    @http.route("/snippet_chart/delete", type="json", auth="public", website=True)
    def snippet_chart_delete(self, chart_id: int, website_id: int) -> dict[str, Any]:
        """
        Delete a snippet chart by its ID for a given website.

        Parameters:
        - chart_id: The unique identifier of the chart to delete.
        - website_id: The website identifier used to scope the chart.

        Returns:
        - A dictionary with `success`: True if deletion was performed or chart not found,
          and optionally `error` with a localized message when the chart is not found
          or an exception occurs.
        """
        result = {"success": True}
        try:
            chart = http.request.env["snippet.chart"].search(
                [("id", "=", chart_id), ("website_id", "=", website_id)], limit=1
            )
            if chart:
                chart.unlink()
            else:
                result.update({"error": _("Chart not found."), "success": False})
        except Exception as e:
            _logger.exception(_("Error deleting snippet chart: %s", str(e)))
            result.update(
                {"error": _("Error deleting snippet chart."), "success": False}
            )
        return result

    @http.route("/snippet_chart/update", type="json", auth="public", website=True)
    def snippet_chart_update(
        self, chart_id: int, website_id: int, **kwargs
    ) -> dict[str, Any]:
        """
        Update an existing snippet chart for a given website.

        Parameters:
        - chart_id: The unique identifier of the chart to update.
        - website_id: The website identifier used to scope the chart.
        - kwargs: Fields to update. Required: `name`, `subtitle`, `data_source`.
          Optional: `description`, `link_text`, `link_url`, `chart_type` (default `bar`),
          `data_source_type` (default `internal`), `color` (default `blue`),
          `is_published` (default `True`).

        Returns:
        - A dictionary with `success`: True on successful update, otherwise False.
          Includes `error` with a localized message when required fields are missing,
          the chart is not found, or an exception occurs.
        """
        required_fields = ["name", "subtitle", "data_source"]
        if not all(kwargs.get(field) for field in required_fields):
            return {"success": False, "error": _("Missing required fields.")}
        result = {"success": True}
        try:
            chart = http.request.env["snippet.chart"].search(
                [("id", "=", chart_id), ("website_id", "=", website_id)], limit=1
            )
            if chart:
                chart.write(
                    {
                        "name": kwargs["name"],
                        "subtitle": kwargs["subtitle"],
                        "description": kwargs.get("description", False),
                        "link_text": kwargs.get("link_text", False),
                        "link_url": kwargs.get("link_url", False),
                        "chart_type": kwargs.get("chart_type", "bar"),
                        "data_source_type": kwargs.get("data_source_type", "internal"),
                        "data_source": kwargs["data_source"],
                        "color": kwargs.get("color", "blue"),
                        "is_published": kwargs.get("is_published", True),
                    }
                )
            else:
                result.update({"error": _("Chart not found."), "success": False})
        except Exception as e:
            _logger.exception(_("Error updating snippet chart: %s", str(e)))
            result.update(
                {"error": _("Error updating snippet chart."), "success": False}
            )
        return result

    @http.route("/snippet_chart/create", type="json", auth="public", website=True)
    def snippet_chart_create(self, website_id: int, **kwargs) -> dict[str, Any]:
        """
        Create a new snippet chart for a given website.

        Parameters:
        - website_id: The website identifier to associate the chart with.
        - kwargs: Fields for chart creation. Required: `name`, `subtitle`, `data_source`.
          Optional: `description`, `link_text`, `link_url`, `chart_type` (default `bar`),
          `data_source_type` (default `internal`), `color` (default `blue`),
          `is_published` (default `True`).

        Returns:
        - A dictionary with `success`: True on successful creation, otherwise False.
          Includes `error` with a localized message when required fields are missing
          or an exception occurs.
        """
        required_fields = ["name", "subtitle", "data_source"]
        if not all(kwargs.get(field) for field in required_fields):
            return {"success": False, "error": _("Missing required fields.")}
        result = {"success": True}
        try:
            http.request.env["snippet.chart"].create(
                {
                    "name": kwargs["name"],
                    "subtitle": kwargs["subtitle"],
                    "description": kwargs.get("description", False),
                    "link_text": kwargs.get("link_text", False),
                    "link_url": kwargs.get("link_url", False),
                    "chart_type": kwargs.get("chart_type", "bar"),
                    "data_source_type": kwargs.get("data_source_type", "internal"),
                    "data_source": kwargs["data_source"],
                    "color": kwargs.get("color", "blue"),
                    "website_id": website_id,
                    "is_published": kwargs.get("is_published", True),
                }
            )
        except Exception as e:
            _logger.exception(_("Error creating snippet chart: %s", str(e)))
            result.update(
                {"error": _("Error creating snippet chart."), "success": False}
            )
        return result
