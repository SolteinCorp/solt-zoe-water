# -*- coding: utf-8 -*-
# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import api, models


class SaleOrderOption(models.Model):
    _inherit = "sale.order.option"

    @api.depends("order_id.order_line.plan_id")
    def _compute_price_unit(self):
        """Recompute price unit when plan changes on order lines."""
        return super()._compute_price_unit()

    @api.depends("order_id.order_line.plan_id")
    def _compute_discount(self):
        """Recompute discount when plan changes on order lines."""
        return super()._compute_discount()

    def _get_values_to_add_to_order(self):
        """Remove discount from values when order is a subscription without discount."""
        option_values = super()._get_values_to_add_to_order()
        if self.order_id.is_subscription and not self.discount:
            option_values.pop("discount")
        return option_values
