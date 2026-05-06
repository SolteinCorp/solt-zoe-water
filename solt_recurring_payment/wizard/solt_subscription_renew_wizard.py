# -*- coding: utf-8 -*-

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class SoltSubscriptionRenewWizardLine(models.TransientModel):
    _name = "solt.subscription.renew.wizard.line"
    _description = "Subscription Wizard Line"

    wizard_id = fields.Many2one(
        "solt.subscription.renew.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
        help="Parent wizard that owns this line.",
    )
    line_type = fields.Selection(
        [
            ("upsell", "Upsell"),
            ("service_change", "Service Change"),
        ],
        string="Line Type",
        required=True,
        default="upsell",
        help="Determines whether this line is an upsell addition or part of a service change.",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        help="Product to add or include in the new service set.",
    )
    product_uom_qty = fields.Float(
        string="Quantity",
        default=1.0,
        required=True,
        help="Quantity of the product.",
    )
    price_unit = fields.Float(
        string="Unit Price",
        digits="Product Price",
        help="Leave empty to auto-resolve from recurring pricing or product list price.",
    )
    name = fields.Text(
        string="Description",
        help="Leave empty to use the product default description.",
    )


class SoltSubscriptionRenewWizard(models.TransientModel):
    _name = "solt.subscription.renew.wizard"
    _description = "Subscription Renew/Change Plan Wizard"

    subscription_id = fields.Many2one(
        "solt.subscription",
        string="Subscription",
        required=True,
        default=lambda self: self.env.context.get("active_id"),
        help="The subscription to manage.",
    )
    action_type = fields.Selection(
        [
            ("renew", "Renew Subscription"),
            ("change_plan", "Change Plan"),
            ("service_change", "Change Services"),
            ("upsell", "Add Products"),
        ],
        string="Action",
        required=True,
        default="renew",
        help="Select the type of change to apply to the subscription.",
    )

    # Current subscription info (readonly)
    current_plan_id = fields.Many2one(
        "solt.recurring.plan",
        related="subscription_id.plan_id",
        string="Current Plan",
    )

    # For change_plan action
    new_plan_id = fields.Many2one(
        "solt.recurring.plan",
        string="New Plan",
        help="Select the new plan to switch to.",
    )
    available_plan_ids_domain = fields.Binary(
        string="Available Plans Domain",
        compute="_compute_available_plan_ids_domain",
        compute_sudo=True,
        help="Computed domain restricting selectable plans to those related to the current plan.",
    )

    # For renew action
    extend_months = fields.Integer(
        string="Extend by (months)",
        default=12,
        help="Number of months to extend the subscription by.",
    )

    # For upsell action
    upsell_line_ids = fields.One2many(
        "solt.subscription.renew.wizard.line",
        "wizard_id",
        string="Products to Add",
        domain=[("line_type", "=", "upsell")],
        context={"default_line_type": "upsell"},
        help="Products to add to the current subscription as an upsell.",
    )

    # For service_change action
    service_change_line_ids = fields.One2many(
        "solt.subscription.renew.wizard.line",
        "wizard_id",
        string="New Product Set",
        domain=[("line_type", "=", "service_change")],
        context={"default_line_type": "service_change"},
        help="Complete product set for the new subscription created by the service change.",
    )
    service_change_plan_id = fields.Many2one(
        "solt.recurring.plan",
        string="Plan for New Subscription",
        help="Leave empty to keep the same plan.",
    )

    @api.depends("subscription_id", "subscription_id.plan_id")
    def _compute_available_plan_ids_domain(self):
        """Compute domain for available plans based on current plan's related plans."""
        for record in self:
            domain = [(0, "=", 1)]
            if record.subscription_id and record.subscription_id.plan_id:
                available_plans = record.subscription_id.available_plan_ids
                if available_plans:
                    domain = [("id", "in", available_plans.ids)]
            record.available_plan_ids_domain = domain

    def action_confirm(self):
        """Execute the selected action."""
        self.ensure_one()

        action_handlers = {
            "change_plan": self._action_change_plan,
            "renew": self._action_renew,
            "upsell": self._action_upsell,
            "service_change": self._action_service_change,
        }
        handler = action_handlers.get(self.action_type)
        if handler:
            return handler()

    # === CHANGE PLAN (IN-PLACE) === #

    def _action_change_plan(self):
        """Change plan in-place: update plan, recalculate prices, prorate, adjust billing."""
        if not self.new_plan_id:
            raise UserError(_("Please select a new plan."))
        if self.new_plan_id == self.subscription_id.plan_id:
            raise UserError(_("The new plan must be different from the current plan."))
        if self.subscription_id.state != "active":
            raise UserError(_("Plan can only be changed for active subscriptions."))

        self.subscription_id.sudo()._change_plan_inplace(self.new_plan_id)

        return {
            "type": "ir.actions.act_window",
            "res_model": "solt.subscription",
            "res_id": self.subscription_id.id,
            "view_mode": "form",
            "target": "current",
        }

    # === RENEW === #

    def _action_renew(self):
        """Renew the subscription: extend end date and reactivate if closed."""
        if self.extend_months <= 0:
            raise UserError(_("Please enter a positive number of months."))

        from dateutil.relativedelta import relativedelta

        subscription = self.subscription_id
        current_end = subscription.end_date or subscription.next_invoice_date
        if not current_end:
            current_end = fields.Date.today()

        new_end_date = current_end + relativedelta(months=self.extend_months)
        subscription_sudo = subscription.sudo()
        subscription_sudo.end_date = new_end_date

        if subscription.state == "closed":
            subscription_sudo.set_open()
            subscription.message_post(
                body=_(
                    "Subscription renewed and reopened. Extended by %d months. New end date: %s",
                    self.extend_months,
                    new_end_date,
                )
            )
        else:
            subscription.message_post(
                body=_(
                    "Subscription extended by %d months. New end date: %s",
                    self.extend_months,
                    new_end_date,
                )
            )

        return {"type": "ir.actions.act_window_close"}

    # === UPSELL === #

    def _action_upsell(self):
        """Upsell: add new product lines to active subscription with proration."""
        if self.subscription_id.state != "active":
            raise UserError(_("Upsell is only available for active subscriptions."))
        if not self.upsell_line_ids:
            raise UserError(_("Please add at least one product to upsell."))

        self.subscription_id.sudo()._upsell_add_lines(self.upsell_line_ids)

        return {
            "type": "ir.actions.act_window",
            "res_model": "solt.subscription",
            "res_id": self.subscription_id.id,
            "view_mode": "form",
            "target": "current",
        }

    # === SERVICE CHANGE === #

    def _action_service_change(self):
        """Service change: create new subscription with different products, transfer instances."""
        if self.subscription_id.state != "active":
            raise UserError(_("Service change is only available for active subscriptions."))
        if not self.service_change_line_ids:
            raise UserError(_("Please define the new product set."))

        subscription = self.subscription_id
        target_plan = self.service_change_plan_id or subscription.plan_id

        # Create new subscription in draft with the new product set
        new_subscription = subscription.sudo().copy(
            {
                "plan_id": target_plan.id,
                "origin_subscription_id": subscription.id,
                "state": "draft",
                "start_date": fields.Date.today(),
                "subscription_line_ids": [],
            }
        )

        # Create lines from wizard selection
        for wizard_line in self.service_change_line_ids:
            resolved_price = wizard_line.price_unit
            if not resolved_price:
                resolved_price = self.env["solt.subscription.line"]._get_price_from_pricing(
                    wizard_line.product_id,
                    target_plan,
                    subscription.pricelist_id,
                    subscription.currency_id,
                    subscription.company_id,
                )

            product_taxes = wizard_line.product_id.taxes_id.filtered(lambda tax: tax.company_id == subscription.company_id)

            self.env["solt.subscription.line"].create(
                {
                    "subscription_id": new_subscription.id,
                    "product_id": wizard_line.product_id.id,
                    "name": wizard_line.name or wizard_line.product_id.get_product_multiline_description_sale(),
                    "product_uom_qty": wizard_line.product_uom_qty,
                    "price_unit": resolved_price,
                    "product_uom": wizard_line.product_id.uom_id.id,
                    "tax_ids": [Command.set(product_taxes.ids)],
                }
            )

        # Prepare and execute service change (hook for integration)
        service_change_data = subscription._prepare_service_change_data(new_subscription)
        subscription._execute_service_change(service_change_data)

        # Generate credit note for unused period on old subscription
        subscription.sudo()._create_unused_period_credit_note()

        # Close old subscription and activate new one
        new_subscription.sudo().action_confirm()
        subscription.sudo().set_close(
            close_reason_id=self.env.ref(
                "solt_recurring_payment.solt_close_reason_plan_change",
                raise_if_not_found=False,
            ).id
            or False,
        )

        subscription.message_post(
            body=_(
                "Service change completed. New subscription: %s",
                new_subscription._get_html_link(),
            )
        )
        new_subscription.message_post(
            body=_(
                "Created from service change. Previous subscription: %s",
                subscription._get_html_link(),
            )
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "solt.subscription",
            "res_id": new_subscription.id,
            "view_mode": "form",
            "target": "current",
        }
