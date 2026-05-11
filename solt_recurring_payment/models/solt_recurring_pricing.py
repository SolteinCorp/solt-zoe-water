# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round


class SoltSaleRecurringPricing(models.Model):
    _name = 'solt.recurring.pricing'
    _description = 'Pricing rule of recurring payment products'
    _order = 'product_template_id, price, plan_id'

    name = fields.Char(related="plan_id.billing_period_display")
    product_template_id = fields.Many2one('product.template', string="Products", ondelete='cascade',
        help="Select products on which this pricing will be applied.")
    product_variant_ids = fields.Many2many('product.product', string="Product Variants",
        help="Select Variants of the Product for which this rule applies. Leave empty if this rule applies for any variant of this template.")
    plan_id = fields.Many2one('solt.recurring.plan', string='Recurring Plan', required=True, help="Select the recurring plan to which this pricing rule applies.")
    company_id = fields.Many2one('res.company', related='plan_id.company_id', help="Company associated with the selected recurring plan.", string="Company")
    price = fields.Monetary(string="Recurring Price", required=True, default=1.0,
        help="Base list price for the (product, plan) tuple. Pricelist rules with a matching plan_id are applied on top of this price, exactly like for non-recurring products.")
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency_id', store=True, help="Currency in which the recurring price is set.")
    required_recurring_quantity = fields.Integer(
        string='Required Recurring Quantity',
        compute='_compute_required_recurring_quantity',
        store=True,
        readonly=False,
        precompute=True,
        help="Minimum quantity of recurring periods that must be purchased with this pricing. "
             "When the plan is prepaid, this is auto-set to the plan's ``billing_period_value`` "
             "and locked (the prepaid commitment covers the full plan period).",
    )
    free_periods = fields.Integer('Free Periods', help="Number of free recurring periods offered with this pricing. Each unit is a full plan period (e.g. 1 = one full year free on an annual plan).")
    prepaid = fields.Boolean(
        related='plan_id.prepaid',
        store=True,
        readonly=True,
        help="True when the linked plan is configured as prepaid. The prepaid flag now lives on "
             "``solt.recurring.plan`` so every pricing on the same plan shares the same prepaid "
             "semantics.",
    )

    @api.depends('plan_id', 'plan_id.prepaid', 'plan_id.billing_period_value')
    def _compute_required_recurring_quantity(self):
        for pricing in self:
            if pricing.plan_id.prepaid:
                pricing.required_recurring_quantity = pricing.plan_id.billing_period_value
            else:
                pricing.required_recurring_quantity = pricing.required_recurring_quantity or 0

    @api.constrains('plan_id', 'product_template_id', 'product_variant_ids')
    def _unique_pricing_constraint(self):
        pricings_per_group = self.read_group(
            ['|', ('product_template_id', 'in', self.product_template_id.ids), ('product_variant_ids', 'in', self.product_variant_ids.ids)],
            ['product_variant_ids:array_agg'],
            ['product_template_id', 'plan_id'], lazy=False)
        for pricings in pricings_per_group:
            if pricings['__count'] < 2:
                continue
            if len(set(pricings['product_variant_ids'])) != len(pricings['product_variant_ids']):
                raise UserError(_("There are multiple pricings for the same product and plan."))

    @api.depends('plan_id', 'plan_id.company_id', 'plan_id.company_id.currency_id')
    def _compute_currency_id(self):
        for pricing in self:
            pricing.currency_id = pricing.plan_id.company_id.currency_id or self.env.company.currency_id

    def _applies_to(self, product):
        """ Check whether current pricing applies to given product.
        :param product.product product:
        :return: true if current pricing is applicable for given product, else otherwise.
        """
        self.ensure_one()
        return self.product_template_id == product.product_tmpl_id and (not self.product_variant_ids or product in self.product_variant_ids)

    @api.model
    def _get_first_suitable_recurring_pricing(self, product, plan=None):
        """Return the (product, plan) list price record for a subscription line.

        Pricelist discounts are NOT evaluated here — they are applied on top by
        the standard pricelist engine through `product.pricelist.item.plan_id`.
        """
        if self.env.is_superuser():
            product = product.sudo()
        is_product_template = product._name == "product.template"
        for pricing in product.product_subscription_pricing_ids:
            if plan and pricing.plan_id != plan:
                continue
            if is_product_template or pricing._applies_to(product):
                return pricing
        return self.env['solt.recurring.pricing']

    @api.model
    def _apply_pricelist_rule(self, base_price, pricelist, product, plan, quantity, uom, date, currency=None):
        """Apply the pricelist rule scoped to the given plan on top of `base_price`.

        Mirrors `product.pricelist.item._compute_price` but uses the recurring
        pricing as the source list_price instead of the product's lst_price.
        """
        if not pricelist or not plan:
            return base_price
        # Two-pass resolution so plan-specific rules win over plan-agnostic ones.
        plan_ctx = pricelist.with_context(plan_id=plan.id, plan_strict=True)
        rule_id = plan_ctx._get_product_rule(product, quantity, uom=uom, date=date)
        if not rule_id:
            agnostic_ctx = pricelist.with_context(plan_id=plan.id)
            rule_id = agnostic_ctx._get_product_rule(product, quantity, uom=uom, date=date)
        if not rule_id:
            return base_price
        rule = self.env['product.pricelist.item'].browse(rule_id)
        if rule.compute_price == 'fixed':
            return rule.fixed_price
        if rule.compute_price == 'percentage':
            return base_price * (1 - rule.percent_price / 100.0)
        if rule.compute_price == 'formula':
            price = base_price
            if rule.price_discount:
                price *= (1 - rule.price_discount / 100.0)
            if rule.price_round:
                price = float_round(price, precision_rounding=rule.price_round)
            if rule.price_surcharge:
                price += rule.price_surcharge
            if rule.price_min_margin:
                price = max(price, base_price + rule.price_min_margin)
            if rule.price_max_margin:
                price = min(price, base_price + rule.price_max_margin)
            return price
        return base_price
