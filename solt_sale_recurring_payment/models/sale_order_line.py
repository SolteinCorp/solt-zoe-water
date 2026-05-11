# -*- coding: utf-8 -*-
from odoo import Command, api, fields, models

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
        """Set price_unit from the (product, plan) list price + pricelist rule."""
        if not self.product_id or not self.plan_id:
            return
        Pricing = self.env["solt.recurring.pricing"]
        pricing = Pricing._get_first_suitable_recurring_pricing(self.product_id, self.plan_id)
        if pricing:
            self.required_recurring_quantity = pricing.required_recurring_quantity
            self.free_periods = pricing.free_periods or 0
            base_price = pricing.currency_id._convert(
                pricing.price,
                self.currency_id,
                self.company_id,
                fields.Date.today(),
            )
            self.price_unit = Pricing._apply_pricelist_rule(
                base_price, self.order_id.pricelist_id,
                self.product_id, self.plan_id,
                self.product_uom_qty or 1.0, self.product_uom,
                self.order_id.date_order or fields.Date.today(),
                currency=self.currency_id,
            )

    # === PRICE COMPUTING HOOKS === #
    def _get_pricelist_price(self):
        """For recurring lines use the (product, plan) list price as the source,
        then let the pricelist rule (filtered by plan_id) reduce it.
        """
        if self.recurring_ok and self.plan_id:
            Pricing = self.env["solt.recurring.pricing"]
            pricing = Pricing._get_first_suitable_recurring_pricing(self.product_id, self.plan_id)
            if pricing:
                base_price = pricing.currency_id._convert(
                    pricing.price, self.currency_id, self.company_id, fields.Date.today(),
                )
                return Pricing._apply_pricelist_rule(
                    base_price, self.order_id.pricelist_id,
                    self.product_id, self.plan_id,
                    self.product_uom_qty or 1.0, self.product_uom,
                    self.order_id.date_order or fields.Date.today(),
                    currency=self.currency_id,
                )
        return super()._get_pricelist_price()

    def _compute_pricelist_item_id(self):
        """Pass plan_id in context so the pricelist engine resolves the right
        plan-scoped item for recurring lines.
        """
        regular = self.filtered(lambda l: not l.recurring_ok or not l.plan_id)
        result = super(SaleOrderLine, regular)._compute_pricelist_item_id()
        for line in self - regular:
            super(SaleOrderLine, line.with_context(plan_id=line.plan_id.id))._compute_pricelist_item_id()
        return result

    def _get_prepaid_pricing(self):
        """Return the matching solt.recurring.pricing record for this line if it
        applies AND is marked as prepaid. Empty recordset otherwise.
        """
        self.ensure_one()
        if not self.recurring_ok or not self.plan_id or not self.product_id:
            return self.env["solt.recurring.pricing"]
        pricing = self.env["solt.recurring.pricing"]._get_first_suitable_recurring_pricing(
            self.product_id, self.plan_id,
        )
        return pricing if pricing.prepaid else self.env["solt.recurring.pricing"]

    def _prepare_invoice_line(self, **optional_values):
        """Override to add subscription info. Prepaid lines used to be expanded
        here (qty × required_recurring_quantity); they're now split into a
        regular line (first period) + a downpayment line (remaining periods)
        by ``sale.order._create_invoices``. The regular line keeps its
        periodic qty.
        """
        invoice_line_values = super()._prepare_invoice_line(**optional_values)
        if self.recurring_ok and (self.subscription_id or self.subscription_line_ids):
            invoice_line_values.update({"subscription_id": (self.subscription_id or self.subscription_line_ids.subscription_id).id})
        return invoice_line_values

    def _get_prepaid_periods_for_invoice(self):
        """How many periods the customer is paying for upfront on this line.

        - Prepaid recurring line: its own pricing's ``required_recurring_quantity``.
        - Delivery line on a SO that has prepaid lines: the SO's max prepaid
          periods (one shipment per prepaid period).
        - Anything else: 1 (no upfront commitment beyond the line itself).
        """
        self.ensure_one()
        pricing = self._get_prepaid_pricing()
        if pricing and pricing.required_recurring_quantity > 1:
            return pricing.required_recurring_quantity
        if getattr(self, "is_delivery", False):
            order_max = self.order_id._get_max_prepaid_periods()
            if order_max > 1:
                return order_max
        return 1

    def _prepare_invoice_downpayment_line(self, inv_line, periods):
        """Return invoice-line vals for the customer-advance portion of a
        prepaid SO line.

        The first period stays on ``inv_line`` (regular, recognised as
        revenue); this method returns the line that parks the remaining
        ``periods - 1`` periods in the customer advance account (the same
        account the standard ``sale.advance.payment.inv`` wizard uses).
        """
        self.ensure_one()
        if periods <= 1:
            return {}
        product_account = self.product_id.product_tmpl_id.get_product_accounts(
            fiscal_pos=self.order_id.fiscal_position_id,
        )
        account = product_account.get("downpayment") or product_account.get("income")
        downpayment_qty = inv_line.quantity * (periods - 1)
        vals = {
            "name": "%s (Anticipo)" % (inv_line.name or self.product_id.display_name),
            "product_id": self.product_id.id,
            "product_uom_id": inv_line.product_uom_id.id,
            "quantity": downpayment_qty,
            "price_unit": inv_line.price_unit,
            "discount": inv_line.discount,
            "tax_ids": [Command.set(inv_line.tax_ids.ids)],
            "sale_line_ids": [Command.set(self.ids)],
            "is_downpayment": True,
        }
        if account:
            vals["account_id"] = account.id if hasattr(account, "id") else account
        if inv_line.analytic_distribution:
            vals["analytic_distribution"] = inv_line.analytic_distribution
        if "subscription_id" in inv_line._fields and inv_line.subscription_id:
            vals["subscription_id"] = inv_line.subscription_id.id
        return vals

    # === AMOUNT COMPUTATION ===
    # The SO line keeps ``product_uom_qty`` at the periodic amount (e.g. 2 bottles
    # per month) so the subscription line spawned from it bills the right qty
    # each cycle. But the *order total* (and therefore the cart and the online
    # payment amount) must reflect what the customer is committing to upfront:
    # qty × price × required_recurring_quantity. We inject the expanded
    # quantity at the tax-computation layer; both the line-level
    # ``_compute_amount`` and the order-level ``_compute_amounts`` go through
    # ``_prepare_base_line_for_taxes_computation``, so a single override here
    # propagates the prepaid total into ``price_subtotal``/``price_tax``/
    # ``price_total`` of the line AND ``amount_untaxed``/``amount_total`` of
    # the order.
    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        if "quantity" not in kwargs:
            pricing = self._get_prepaid_pricing()
            if pricing and pricing.required_recurring_quantity > 1:
                # Prepaid recurring line: customer commits to N periods upfront.
                kwargs["quantity"] = self.product_uom_qty * pricing.required_recurring_quantity
            elif getattr(self, "is_delivery", False):
                # Delivery line on a SO that has prepaid lines: charge N
                # shipments upfront, one per prepaid period.
                periods = self.order_id._get_max_prepaid_periods()
                if periods > 1:
                    kwargs["quantity"] = self.product_uom_qty * periods
        return super()._prepare_base_line_for_taxes_computation(**kwargs)

    @api.depends("plan_id", "required_recurring_quantity")
    def _compute_amount(self):  # pylint: disable=W8110
        # Extends standard depends so the line totals recompute when the plan
        # (and therefore the prepaid period count) changes.
        return super()._compute_amount()

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
