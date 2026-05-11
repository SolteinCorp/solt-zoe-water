# -*- coding: utf-8 -*-
import logging
from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.addons.solt_recurring_payment.models.solt_recurring_order_line_mixin import RecurringOrderLineMixin
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

INTERVAL_FACTOR = {
    "day": 30.437,
    "week": 30.437 / 7.0,
    "month": 1.0,
    "year": 1.0 / 12.0,
}


class RecurringOrderMixin(models.AbstractModel):
    """Mixin to add subscription/recurring functionality to orders (Sale and Purchase)."""

    _name = "solt.recurring.order.mixin"
    _description = "Recurring Order Mixin"

    is_subscription = fields.Boolean(
        string="Has Subscriptions",
        compute="_compute_is_subscription",
        store=True,
        default=False,
        copy=False,
        help="Indicates if this order has recurring product lines.",
    )
    subscription_ids = fields.Many2many(
        "solt.subscription",
        compute="_compute_subscription_ids",
        string="Subscriptions",
        readonly=True,
        copy=False,
        help="Subscriptions created from this sale order.",
    )
    subscription_count = fields.Integer(
        string="Subscription Count",
        readonly=True,
        copy=False,
        compute="_compute_subscription_ids",
        help="Count of subscriptions.",
    )

    # === COMPUTED FIELDS === #
    recurring_total = fields.Float(
        compute="_compute_recurring_total",
        string="Recurring Total",
        store=True,
        help="Recurring total for this order.",
    )
    recurring_monthly = fields.Float(
        compute="_compute_recurring_monthly",
        string="Monthly Recurring",
        store=True,
        help="Recurring monthly for this order.",
    )

    # === QUOTATION DISPLAY FIELDS === #
    subscription_period_total = fields.Json(
        compute="_compute_subscription_period_total",
        string="Resumen de Suscripciones",
        store=True,
        help="Summary of subscription totals grouped by plan (for quotation display only). Contains plan information and period totals.",
    )

    @api.depends("order_line.subscription_id")
    def _compute_subscription_ids(self):
        subscriptions = self.env["solt.subscription"].read_group(
            domain=[("origin_id", "in", self.mapped(lambda rec: f"{rec._name},{rec.id}"))],
            fields=["ids:array_agg(id)"],
            groupby=["origin_id"],
            lazy=False,
        )
        subs_map = defaultdict(list)
        for sub in subscriptions:
            order_id = int(sub["origin_id"].split(",")[1])
            subs_map[order_id].extend(sub["ids"])
        for order in self:
            order.subscription_ids = tuple(subs_map.get(order.id, []))
            order.subscription_count = len(subs_map.get(order.id, []))

    # === COMPUTE METHODS === #
    @api.depends("order_line.recurring_ok", "subscription_ids", "state")
    def _compute_is_subscription(self):
        for order in self:
            order.is_subscription = any(order.order_line.mapped("plan_id"))

    @api.depends("order_line.recurring_ok", "order_line.price_subtotal")
    def _compute_recurring_total(self):
        for order in self:
            recurring_lines = order.order_line.filtered("recurring_ok")
            order.recurring_total = sum(recurring_lines.mapped("price_subtotal"))

    @api.depends("order_line.recurring_monthly")
    def _compute_recurring_monthly(self):
        for order in self:
            order.recurring_monthly = sum(order.order_line.mapped("recurring_monthly"))

    @api.depends(
        "order_line.recurring_ok",
        "order_line.product_id",
        "order_line.plan_id",
        "order_line.price_subtotal",
        "order_line.required_recurring_quantity",
        "order_line.subscription_period_total",
        "currency_id",
    )
    def _compute_subscription_period_total(self):
        """Compute subscription summary grouped by plan for quotation display as JSON."""
        for order in self:
            if not order.is_subscription:
                order.subscription_period_total = None
                continue

            # Separate subscription and non-subscription lines
            subscription_lines = order.order_line.filtered(lambda line: line.plan_id)
            non_subscription_lines = order.order_line.filtered(lambda line: not line.plan_id)

            # Group subscription lines by plan
            plans_data = {}
            amount_subscription_subtotal = 0.0
            amount_subscription_tax = 0.0
            amount_subscription_total = 0.0
            labels = dict(self.env["solt.recurring.plan"]._fields["billing_period_unit"]._description_selection(self.env))
            for line in subscription_lines:
                plan = line.plan_id
                if plan.id not in plans_data:
                    plans_data[plan.id] = {
                        "id": plan.id,
                        "plan_name": plan.name,
                        "plan_id": plan.id,
                        "billing_period_unit": plan.billing_period_unit,
                        "billing_period_display": labels[plan.billing_period_unit],
                        "price_unit": 0.0,
                        "periodic_amount": 0.0,
                        "periodic_tax_amount": 0.0,
                        "period_total": 0.0,
                        "period": line.required_recurring_quantity or 0,
                    }

                AccountTax = self.env["account.tax"].with_company(line.company_id)
                tax_base_line = AccountTax._prepare_base_line_for_taxes_computation(
                    line,
                    tax_ids=line._get_tax_ids(),
                    quantity=line.product_uom_qty * (line.required_recurring_quantity or 1),
                    partner_id=line.order_id.partner_id,
                    currency_id=line.order_id.currency_id,
                )
                AccountTax._add_tax_details_in_base_line(tax_base_line, line.company_id)
                AccountTax._round_base_lines_tax_details([tax_base_line], line.company_id)
                amount_untaxed = tax_base_line["tax_details"]["total_excluded_currency"]
                amount_tax = tax_base_line["tax_details"]["total_included_currency"] - amount_untaxed
                plans_data[plan.id]["price_unit"] += line.price_unit
                plans_data[plan.id]["periodic_amount"] += amount_untaxed
                plans_data[plan.id]["periodic_tax_amount"] += amount_tax
                plans_data[plan.id]["period_total"] += amount_untaxed + amount_tax

                amount_subscription_subtotal += amount_untaxed
                amount_subscription_tax += amount_tax
                amount_subscription_total += amount_untaxed + amount_tax

                # Use the maximum period if lines have different values
                if line.required_recurring_quantity > plans_data[plan.id]["period"]:
                    plans_data[plan.id]["period"] = line.required_recurring_quantity

            # Calculate totals
            amount_non_subscription = sum(non_subscription_lines.mapped("price_subtotal"))
            amount_tax_non_subscription = sum(non_subscription_lines.mapped("price_tax"))
            amount_total_non_subscription = sum(non_subscription_lines.mapped("price_total"))

            amount_subscription_subtotal += amount_non_subscription
            amount_subscription_tax += amount_tax_non_subscription
            amount_subscription_total += amount_total_non_subscription

            # Create the JSON structure
            order.subscription_period_total = {
                "amount_non_subscription": amount_non_subscription,
                "amount_tax_non_subscription": amount_tax_non_subscription,
                "amount_total_non_subscription": amount_total_non_subscription,
                "amount_subscription_subtotal": amount_subscription_subtotal,
                "amount_subscription_tax": amount_subscription_tax,
                "amount_subscription_total": amount_subscription_total,
                "plans": tuple(plans_data.values()),
                "currency_id": order.currency_id.id,
            }

    def _get_recurring_order_line(self) -> RecurringOrderLineMixin:
        """Get recurring order lines."""
        return self.order_line

    def _create_subscriptions(self):
        """
        Create subscriptions from recurring lines.
        Lines are grouped by plan_id to create separate subscriptions.
        The subscription start_date is always the order date.
        The next_invoice_date is calculated from the maximum free_periods of the grouped lines.
        """
        for order in self.filtered("is_subscription"):
            recurring_lines = order._get_recurring_order_line().filtered("plan_id")
            if not recurring_lines:
                continue
            # Validate all recurring lines have a plan
            lines_without_plan = recurring_lines.filtered(lambda line: not line.plan_id)
            if lines_without_plan:
                raise UserError(
                    _(
                        "The following products require a subscription plan:\n%s",
                        "\n".join(lines_without_plan.mapped("product_id.display_name")),
                    )
                )
            # Group lines by plan_id
            groups = {}
            for line in recurring_lines:
                key = line.plan_id.id
                groups.setdefault(key, order.env[line._name])
                groups[key] |= line
            # Create subscriptions
            Subscription = order.env["solt.subscription"]
            for plan_id, lines in groups.items():
                subscription_vals = order._prepare_subscription_values(plan_id, lines)
                subscription = Subscription.create(subscription_vals)
                # Link lines to subscription
                lines.write({"subscription_id": subscription.id})
                _logger.info("Created subscription %s from order %s with %d lines", subscription.name, order.name, len(lines))

    def _prepare_subscription_values(self, plan_id, lines):
        """Prepare values for creating a subscription.

        The start_date is always the order date. ``next_invoice_date`` always
        starts at the order date — ``free_periods`` is checked per subscription
        line at invoicing time (lines still in their free window are skipped
        for that cycle), not by globally offsetting the schedule here.

        For each recurring line we emit one regular subscription line; lines
        flagged as prepaid additionally emit a downpayment subscription line
        (via ``_prepare_subscription_downpayment_line_values``) so the cron can
        apply the prepaid balance as a negative line on subsequent monthly
        invoices, mirroring the native ``sale.advance.payment.inv`` pattern.
        """
        self.ensure_one()
        order_date = self.date_order.date() if hasattr(self.date_order, "date") else self.date_order
        subscription_line_commands = []
        for line in lines:
            subscription_line_commands.append(Command.create(line._prepare_subscription_line_values()))
            downpayment_vals = line._prepare_subscription_downpayment_line_values()
            if downpayment_vals:
                subscription_line_commands.append(Command.create(downpayment_vals))
        return {
            "origin_id": f"{self._name},{self.id}",
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "plan_id": plan_id,
            "start_date": order_date,
            "next_invoice_date": order_date,
            "user_id": self.user_id.id,
            "subscription_line_ids": subscription_line_commands,
        }

    def action_open_subscriptions(self):
        """Open the subscriptions created from this order."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("solt_recurring_payment.solt_subscription_action")
        if self.subscription_count > 1:
            action["domain"] = [("id", "in", self.subscription_ids.ids)]
        elif self.subscription_count == 1:
            action["views"] = [(self.env.ref("solt_recurring_payment.solt_subscription_view_form").id, "form")]
            action["res_id"] = self.subscription_ids.id
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action
