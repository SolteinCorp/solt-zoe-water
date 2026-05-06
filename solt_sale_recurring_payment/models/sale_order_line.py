# -*- coding: utf-8 -*-
from odoo import api, fields, models

INTERVAL_FACTOR = {
    "day": 30.437,
    "week": 30.437 / 7.0,
    "month": 1.0,
    "year": 1.0 / 12.0,
}


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["sale.order.line", "solt.recurring.order.line.mixin"]

    # === ONCHANGE METHODS === #
    @api.onchange("plan_id")
    def _onchange_plan_id(self):
        """When changing plan, update price accordingly."""
        if self.product_id and self.recurring_ok and self.plan_id:
            self._set_price_from_plan()

    def _set_price_from_plan(self):
        """Set price_unit based on the selected plan and pricelist."""
        if not self.product_id or not self.plan_id:
            return
        pricing = self.env["solt.recurring.pricing"]._get_first_suitable_recurring_pricing(self.product_id, self.plan_id, self.order_id.pricelist_id)
        if pricing:
            self.required_recurring_quantity = pricing.required_recurring_quantity
            self.free_periods = pricing.free_periods or 0
            self.price_unit = pricing.currency_id._convert(
                pricing.price,
                self.currency_id,
                self.company_id,
                fields.Date.today(),
            )

    # === PRICE COMPUTING HOOKS === #
    def _get_pricelist_price(self):
        """Override to use subscription pricing for recurring products."""
        if self.recurring_ok and self.plan_id:
            pricing = self.env["solt.recurring.pricing"]._get_first_suitable_recurring_pricing(
                self.product_id, self.plan_id, self.order_id.pricelist_id
            )
            if pricing:
                if pricing.pricelist_id:
                    return pricing.pricelist_id._get_product_price(
                        self.product_id.with_context(**self._get_product_price_context()),
                        self.product_uom_qty or 1.0,
                        currency=self.currency_id,
                        uom=self.product_uom,
                        date=self.order_id.date_order or fields.Date.today(),
                        start_date=fields.Date.today(),
                    )
                return pricing.currency_id._convert(pricing.price, self.currency_id, self.company_id, fields.Date.today())
        return super()._get_pricelist_price()

    def _compute_pricelist_item_id(self):
        """Recurring lines don't use pricelist items."""
        recurring_lines = self.filtered("recurring_ok")
        result = super(SaleOrderLine, self - recurring_lines)._compute_pricelist_item_id()
        recurring_lines.pricelist_item_id = False
        return result

    def _prepare_invoice_line(self, **optional_values):
        """Override to add subscription info to invoice lines."""
        vals = super()._prepare_invoice_line(**optional_values)
        if self.recurring_ok and (self.subscription_id or self.subscription_line_ids):
            vals.update({"subscription_id": (self.subscription_id or self.subscription_line_ids.subscription_id).id})
        return vals

    @api.onchange("product_id")
    def _onchange_product_subscription(self):
        """Clear plan-related fields when switching to a non-recurring product."""
        if not self.product_id or not self.product_id.recurring_ok:
            self.plan_id = False
            self.required_recurring_quantity = 0
            self.free_periods = 0
