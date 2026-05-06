# -*- coding: utf-8 -*-
from odoo import api, models


class SaleOrderOption(models.Model):
    _inherit = "sale.order.option"

    @api.depends("order_id.order_line.plan_id")
    def _compute_price_unit(self):
        return super()._compute_price_unit()

    @api.depends("order_id.order_line.plan_id")
    def _compute_discount(self):
        return super()._compute_discount()

    def _get_values_to_add_to_order(self):
        res = super()._get_values_to_add_to_order()
        if self.order_id.is_subscription and not self.discount:
            res.pop("discount")
        return res
