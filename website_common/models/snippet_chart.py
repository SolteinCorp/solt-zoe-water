# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

"""Snippet Chart Model Definition"""

from odoo import fields, models


class SnippetChart(models.Model):
    """Model for Snippet Chart Configuration"""

    _name = "snippet.chart"
    _inherit = ["website.published.multi.mixin"]
    _description = "Snippet Chart"

    def _default_is_published(self):
        return True

    name = fields.Char(string="Chart Name", required=True, help="Chart Name")
    subtitle = fields.Char(string="Subtitle", required=True, help="Subtitle")
    description = fields.Text(
        string="Description", required=False, help="Description of the chart"
    )
    link_text = fields.Char(string="Link Text", required=False, help="Link Text")
    link_url = fields.Char(string="Link URL", required=False, help="Link URL")
    chart_type = fields.Selection(
        [("bar", "Bar Chart"), ("line", "Line Chart"), ("pie", "Pie Chart")],
        string="Chart Type",
        required=True,
        default="bar",
        help="Chart Type",
    )
    data_source_type = fields.Selection(
        [("internal", "Internal"), ("external", "External")],
        string="Data Source Type",
        required=True,
        default="internal",
        help="Data Source Type",
    )
    data_source = fields.Char(
        string="Data Source", required=True, help="Data Source URL"
    )
    color = fields.Selection(
        [
            ("blue", "Blue"),
            ("orange", "Orange"),
        ],
        string="Color",
        required=True,
        default="blue",
        help="Color for the chart",
    )

    # add unique constraint on name field
    _sql_constraints = [
        (
            "chart_website_name_unique",
            "unique(name, website_id)",
            "Chart Name must be unique in this website.",
        )
    ]
