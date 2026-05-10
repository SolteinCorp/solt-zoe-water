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

    def _get_prepaid_pricing(self):
        """Return the matching solt.recurring.pricing record for this line if it
        applies AND is marked as prepaid. Empty recordset otherwise.
        """
        self.ensure_one()
        if not self.recurring_ok or not self.plan_id or not self.product_id:
            return self.env["solt.recurring.pricing"]
        pricing = self.env["solt.recurring.pricing"]._get_first_suitable_recurring_pricing(
            self.product_id, self.plan_id, self.order_id.pricelist_id,
        )
        return pricing if pricing.prepaid else self.env["solt.recurring.pricing"]

    def _prepare_invoice_line(self, **optional_values):
        """Override to add subscription info and to expand qty for prepaid lines.
        Prepaid lines are billed up front from the SO with qty × required_recurring_quantity.
        """
        invoice_line_values = super()._prepare_invoice_line(**optional_values)
        if self.recurring_ok and (self.subscription_id or self.subscription_line_ids):
            invoice_line_values.update({"subscription_id": (self.subscription_id or self.subscription_line_ids.subscription_id).id})
        prepaid_pricing = self._get_prepaid_pricing()
        if prepaid_pricing:
            invoice_line_values["quantity"] = invoice_line_values.get("quantity", 1) * prepaid_pricing.required_recurring_quantity
        return invoice_line_values

    @api.depends("free_periods")
    def _compute_qty_to_invoice(self):  # pylint: disable=W8110
        """Lines with free_periods > 0 are not invoiced on the SO confirmation:
        the subscription's per-line check defers them until the free window
        elapses and the cron picks them up.
        """
        super()._compute_qty_to_invoice()
        for line in self:
            if line.recurring_ok and line.free_periods > 0:
                line.qty_to_invoice = 0

    @api.onchange("product_id")
    def _onchange_product_subscription(self):
        """Clear plan-related fields when switching to a non-recurring product."""
        if not self.product_id or not self.product_id.recurring_ok:
            self.plan_id = False
            self.required_recurring_quantity = 0
            self.free_periods = 0
