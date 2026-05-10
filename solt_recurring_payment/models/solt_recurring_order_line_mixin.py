# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

INTERVAL_FACTOR = {
    'day': 30.437,
    'week': 30.437 / 7.0,
    'month': 1.0,
    'year': 1.0 / 12.0,
}


class RecurringOrderLineMixin(models.AbstractModel):
    """Mixin to add subscription/recurring functionality to order lines (Sale and Purchase)."""
    _name = 'solt.recurring.order.line.mixin'
    _description = 'Recurring Line Order Mixin'

    # === SUBSCRIPTION FIELDS === #
    recurring_ok = fields.Boolean(
        string="Is Recurring",
        compute="_compute_recurring_invoice",
        store=True,
        default=False,
        help="Indicates if this product line is a recurring (subscription) product."
    )
    plan_id = fields.Many2one(
        'solt.recurring.plan',
        string='Subscription Plan',
        help="Plan for this recurring product line.",
    )
    free_periods = fields.Integer(
        string='Free Periods',
        default=0,
        help="Number of free recurring periods before the first invoice is generated.",
    )
    required_recurring_quantity = fields.Integer(
        'Required Recurring Quantity',
        help="Minimum quantity of recurring periods that must be purchased with this pricing."
    )
    subscription_id = fields.Many2one(
        'solt.subscription',
        string='Subscription',
        readonly=True,
        copy=False,
        help="The subscription created from this line.",
    )
    subscription_line_ids = fields.One2many(
        'solt.subscription.line',
        'origin_line_id',
        string='Subscription Line',
        readonly=True,
        copy=False,
        help="The subscription line created from this line.",
    )

    # === COMPUTED FIELDS === #
    recurring_monthly = fields.Float(
        compute='_compute_recurring_monthly',
        string="Monthly Recurring Revenue",
        help="The monthly recurring revenue (MRR) for this line, computed based on the selected subscription plan and price."
    )
    subscription_period_total = fields.Float(
        compute='_compute_subscription_period_total',
        string="Total del Periodo",
        store=True,
        help="Total amount for the entire subscription period (price_subtotal × required_recurring_quantity). This is informational only for quotations."
    )
    available_plan_ids_domain = fields.Binary(
        string="Available Plans Domain",
        compute="_compute_available_plan_ids_domain",
        compute_sudo=True,
        help="Domain used to filter available subscription plans for this product line."
    )

    @api.depends('product_id')
    def _compute_recurring_invoice(self):
        """Compute whether the line is a recurring invoice based on the product."""
        for line in self:
            line.recurring_ok = bool(line.product_id and line.product_id.recurring_ok)

    @api.constrains('free_periods')
    def _check_free_periods(self):
        """Ensure free_periods is not negative."""
        for line in self:
            if line.free_periods < 0:
                raise ValidationError(_(
                    "The number of free periods cannot be negative for product '%s'.",
                    line.product_id.display_name,
                ))

    # === COMPUTE METHODS === #
    @api.depends('product_id', 'product_id.product_subscription_pricing_ids')
    def _compute_available_plan_ids_domain(self):
        """Compute domain for available plans based on product's subscription pricing."""
        for record in self:
            domain = [(0, '=', 1)]  # Default to empty domain
            if record.product_id and record.recurring_ok:
                pricings = record.product_id.product_subscription_pricing_ids
                plan_ids = pricings.mapped('plan_id').ids
                if plan_ids:
                    domain = [('id', 'in', plan_ids)]
            record.available_plan_ids_domain = domain

    @api.depends('recurring_ok', 'price_subtotal', 'plan_id')
    def _compute_recurring_monthly(self):
        for line in self:
            if not line.recurring_ok or not line.plan_id or not line.plan_id.billing_period:
                line.recurring_monthly = 0
            else:
                factor = INTERVAL_FACTOR.get(line.plan_id.billing_period_unit, 1.0)
                line.recurring_monthly = line.price_subtotal * factor / line.plan_id.billing_period_value

    @api.depends('recurring_ok', 'price_subtotal', 'required_recurring_quantity')
    def _compute_subscription_period_total(self):
        """Compute the total amount for the entire subscription period."""
        for line in self:
            if line.recurring_ok and line.required_recurring_quantity > 0:
                line.subscription_period_total = line.price_subtotal * line.required_recurring_quantity
            else:
                line.subscription_period_total = 0.0

    # === SUBSCRIPTION CREATION === #
    def _prepare_subscription_line_values(self):
        """Prepare values to create a subscription line from this order line."""
        self.ensure_one()
        return {
            'origin_line_id': f'{self._name},{self.id}',
            'product_id': self.product_id.id,
            'name': self.name,
            'product_uom_qty': self._get_product_qty(),
            'product_uom': self.product_uom.id,
            'price_unit': self.price_unit,
            'tax_ids': [(6, 0, self._get_tax_ids().ids)],
            'free_periods': self.free_periods,
        }

    def _get_product_qty(self):
        """Get product quantity. Override in subclasses."""
        return self.product_uom_qty

    def _get_tax_ids(self):
        """Get tax ids. Override in subclasses."""
        return self.tax_id
