# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SoltSaleRecurringPricing(models.Model):
    _name = 'solt.recurring.pricing'
    _description = 'Pricing rule of recurring payment products'
    _order = 'product_template_id, price, pricelist_id, plan_id'

    name = fields.Char(related="plan_id.billing_period_display")
    product_template_id = fields.Many2one('product.template', string="Products", ondelete='cascade',
        help="Select products on which this pricing will be applied.")
    product_variant_ids = fields.Many2many('product.product', string="Product Variants",
        help="Select Variants of the Product for which this rule applies. Leave empty if this rule applies for any variant of this template.")
    plan_id = fields.Many2one('solt.recurring.plan', string='Recurring Plan', required=True, help="Select the recurring plan to which this pricing rule applies.")
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', ondelete='cascade', help="Select the pricelist for which this pricing rule is valid.")
    company_id = fields.Many2one('res.company', related='plan_id.company_id', help="Company associated with the selected recurring plan.", string="Company", )
    price = fields.Monetary(string="Recurring Price", required=True, default=1.0, help="The recurring price to be charged for the selected product and plan.")
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency_id', store=True, help="Currency in which the recurring price is set.")
    required_recurring_quantity = fields.Integer('Required Recurring Quantity', help="Minimum quantity of recurring periods that must be purchased with this pricing.")
    free_periods = fields.Integer('Free Periods', help="Number of free recurring periods offered with this pricing.")

    @api.constrains('plan_id', 'pricelist_id', 'product_template_id', 'product_variant_ids')
    def _unique_pricing_constraint(self):
        pricings_per_group = self.read_group(
            ['|', ('product_template_id', 'in', self.product_template_id.ids), ('product_variant_ids', 'in', self.product_variant_ids.ids)],
            ['product_variant_ids:array_agg'],
            ['product_template_id', 'plan_id', 'pricelist_id'], lazy=False)
        for pricings in pricings_per_group:
            if pricings['__count'] < 2:
                continue
            if len(set(pricings['product_variant_ids'])) != len(pricings['product_variant_ids']):
                raise UserError(_("There are multiple pricings for an unique product, plan and pricelist."))

    @api.constrains('pricelist_id')
    def _unique_company_contraint(self):
        if self.company_id and self.pricelist_id.company_id and self.company_id != self.pricelist_id.company_id:
            raise UserError(_("The company of the plan is different from the company of the pricelist"))

    @api.depends('pricelist_id', 'pricelist_id.currency_id')
    def _compute_currency_id(self):
        for pricing in self:
            pricing.currency_id = pricing.pricelist_id and pricing.pricelist_id.currency_id or self.env.company.currency_id

    def _applies_to(self, product):
        """ Check whether current pricing applies to given product.
        :param product.product product:
        :return: true if current pricing is applicable for given product, else otherwise.
        """
        self.ensure_one()
        return self.product_template_id == product.product_tmpl_id and (not self.product_variant_ids or product in self.product_variant_ids)

    @api.model
    def _get_first_suitable_recurring_pricing(self, product, plan=None, pricelist=None):
        """ Get a suitable pricing for given product and pricelist.
        Note: model method
        """
        if self.env.is_superuser():  # This is for access to the product pricing
            product = product.sudo()
        is_product_template = product._name == "product.template"
        available_pricings = product.product_subscription_pricing_ids
        first_pricing = self.env['solt.recurring.pricing']
        for pricing in available_pricings:
            if plan and pricing.plan_id != plan:
                continue
            if pricing.pricelist_id == pricelist and (is_product_template or pricing._applies_to(product)):
                return pricing
            if not first_pricing and not pricing.pricelist_id and (is_product_template or pricing._applies_to(product)):
                # If price list and current pricing is not part of it,
                # We store the first one to return if not pricing matching the price list is found.
                first_pricing = pricing
        return first_pricing
