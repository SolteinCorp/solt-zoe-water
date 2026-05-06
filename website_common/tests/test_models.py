# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

"""Test models for Odoo module."""

from odoo import fields, models


class ModelA(models.Model):
    """Test model A with basic fields."""

    _name = "model.a"
    _description = "Model A"

    name = fields.Char(string="Name", required=True, help="Name")
    description = fields.Text(string="Description", help="Description")


class ModelB(models.Model):
    """Test model with a Many2one relationship to ModelA."""

    _name = "model.b"
    _description = "Model B"

    title = fields.Char(string="Title", required=True, help="Title")
    model_a_id = fields.Many2one(
        "model.a",
        string="Related Model A",
        ondelete="cascade",
        help="Related Model A",
        help_text="Related Model A",
    )
    active = fields.Boolean(string="Active", default=True)
