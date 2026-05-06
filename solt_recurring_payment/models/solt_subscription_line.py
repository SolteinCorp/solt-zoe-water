# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import Command, api, fields, models
from odoo.tools.float_utils import float_round

INTERVAL_FACTOR = {
    'day': 30.437,
    'week': 30.437 / 7.0,
    'month': 1.0,
    'year': 1.0 / 12.0,
}


class SoltSaleSubscriptionLine(models.Model):
    _name = 'solt.subscription.line'
    _description = 'Subscription Line'
    _order = 'subscription_id, sequence, id'

    subscription_id = fields.Many2one(
        'solt.subscription',
        string='Subscription',
        required=True,
        ondelete='cascade',
        index=True,
        help='The subscription this line belongs to.',
    )
    subscription_type = fields.Selection(
        related='subscription_id.type',
        string='Type',
    )
    origin_line_id = fields.Reference(
        [('sale.order.line', 'Sale Order Line'), ('purchase.order.line', 'Purchase Order Line')],
        string='Origin Line',
        readonly=True,
        copy=False,
        help='The original line from which this subscription line was created.',
    )
    company_id = fields.Many2one(
        string='Company',
        related='subscription_id.company_id',
        store=True,
        help='Company related to the subscription.',
    )
    currency_id = fields.Many2one(
        string='Currency',
        related='subscription_id.currency_id',
        store=True,
        help='Currency used for this subscription line.',
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Gives the sequence order when displaying a list of subscription lines.',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain="[(('recurring_ok', '=', True))]",
        help='Product to be invoiced recurrently.',
    )
    product_template_id = fields.Many2one(
        'product.template',
        string='Product Template',
        related='product_id.product_tmpl_id',
        help='Product template related to the selected product.',
    )
    name = fields.Text(
        string='Description',
        required=True,
        help='Description of the subscription line.',
    )
    product_uom_qty = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        help='Quantity of the product to invoice.',
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
        default=lambda self: self.env.ref('uom.product_uom_unit', raise_if_not_found=False),
        domain="[('category_id', '=', product_uom_category_id)]",
        help='Unit of measure for the product.',
    )
    product_uom_category_id = fields.Many2one(
        string='Category of UOM',
        related='product_id.uom_id.category_id',
        help='UoM category related to the selected product.',
    )
    product_domain = fields.Char(
        string='Product Domain',
        compute='_compute_product_domain',
        help='Domain to filter products based on the subscription type.',
    )
    price_unit = fields.Float(
        string='Unit Price',
        required=True,
        digits='Product Price',
        help='Unit price of the product.',
    )
    discount = fields.Float(
        string='Discount (%)',
        digits='Discount',
        default=0.0,
        help='Discount applied to the unit price (in percentage).',
    )
    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        domain="[('type_tax_use', '=', subscription_type), ('company_id', '=', company_id)]",
        help='Taxes applied to this subscription line.',
    )
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_amounts',
        store=True,
        help='Subtotal amount without taxes.',
    )
    price_tax = fields.Monetary(
        string='Tax Amount',
        compute='_compute_amounts',
        store=True,
        help='Total tax amount for this line.',
    )
    price_total = fields.Monetary(
        string='Total',
        compute='_compute_amounts',
        store=True,
        help='Total amount including taxes.',
    )
    recurring_monthly = fields.Monetary(
        string='Monthly Recurring',
        compute='_compute_recurring_monthly',
        store=True,
        help='Monthly recurring amount for this line, normalized to a monthly value.',
    )
    currency_rate = fields.Float(
        compute='_compute_currency_rate',
        help="Currency rate from company currency to document currency."
    )

    @api.depends('currency_id', 'company_id', 'subscription_id.next_invoice_date', 'subscription_id.end_date')
    def _compute_currency_rate(self):
        for line in self:
            if line.currency_id:
                line.currency_rate = self.env['res.currency']._get_conversion_rate(
                    from_currency=line.company_id.currency_id,
                    to_currency=line.currency_id,
                    company=line.company_id,
                    date=line.subscription_id.end_date or line.subscription_id.next_invoice_date or fields.Date.context_today(line)
                )
            else:
                line.currency_rate = 1

    @api.depends('subscription_type')
    def _compute_product_domain(self):
        """Compute the product domain based on the subscription type."""
        for line in self:
            if line.subscription_type == 'sale':
                line.product_domain = "[('sale_ok', '=', True)]"
            elif line.subscription_type == 'purchase':
                line.product_domain = "[('purchase_ok', '=', True)]"
            else:
                line.product_domain = "[(0, '=', 1)]"

    @api.depends('product_uom_qty', 'price_unit', 'discount', 'tax_ids')
    def _compute_amounts(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            quantity = line.product_uom_qty
            subtotal = price * quantity

            if line.tax_ids:
                taxes = line.tax_ids.compute_all(
                    price,
                    currency=line.currency_id,
                    quantity=quantity,
                    product=line.product_id,
                    partner=line.subscription_id.partner_id,
                )
                line.price_subtotal = taxes['total_excluded']
                line.price_tax = taxes['total_included'] - taxes['total_excluded']
                line.price_total = taxes['total_included']
            else:
                line.price_subtotal = subtotal
                line.price_tax = 0.0
                line.price_total = subtotal

    @api.depends('price_subtotal', 'subscription_id.plan_id.billing_period_unit', 'subscription_id.plan_id.billing_period_value')
    def _compute_recurring_monthly(self):
        for line in self:
            plan = line.subscription_id.plan_id
            if not plan or not plan.billing_period_unit or not plan.billing_period_value:
                line.recurring_monthly = 0
            else:
                factor = INTERVAL_FACTOR.get(plan.billing_period_unit, 1.0)
                line.recurring_monthly = line.price_subtotal * factor / plan.billing_period_value

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Dispatch product data setup based on subscription type."""
        if not self.product_id:
            return

        if self.subscription_type == 'purchase':
            self._set_purchase_product_data()
        else:
            self._set_sale_product_data()

    def _set_purchase_product_data(self):
        """Set product data for purchase subscriptions using vendor prices."""
        self.ensure_one()
        if not self.product_id:
            return

        self.name = self.product_id.display_name
        if self.product_id.description_purchase:
            self.name += '\n' + self.product_id.description_purchase
        self.product_uom_id = self.product_id.uom_po_id or self.product_id.uom_id
        self.tax_ids = self.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == self.company_id)

        price_data = self._get_purchase_price_data()
        self.price_unit = price_data['price_unit']
        self.discount = price_data.get('discount', 0.0)

    def _get_purchase_price_data(self):
        """Get price data for purchase subscriptions from vendor/seller records.

        :return: dict with 'price_unit' and 'discount'
        """
        self.ensure_one()
        if not self.product_id:
            return {'price_unit': 0.0, 'discount': 0.0}

        plan = self.subscription_id.plan_id
        partner = self.subscription_id.partner_id

        if not plan:
            return {'price_unit': self.product_id.standard_price, 'discount': 0.0}

        product_uom = self.product_uom_id or self.product_id.uom_po_id or self.product_id.uom_id
        tax_ids = self.tax_ids or self.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == self.company_id)

        seller = self.product_id._select_seller(
            partner_id=partner,
            quantity=self.product_uom_qty,
            date=fields.Date.today(),
            uom_id=product_uom,
        )

        if seller:
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                seller.price, self.product_id.supplier_taxes_id, tax_ids, self.company_id
            )
            price_unit = seller.currency_id._convert(
                price_unit, self.currency_id, self.company_id, fields.Date.today(), False
            )
            price_unit = float_round(
                price_unit,
                precision_digits=max(
                    self.currency_id.decimal_places,
                    self.env['decimal.precision'].precision_get('Product Price'),
                ),
            )
            price_unit = seller.product_uom._compute_price(price_unit, product_uom)
            return {'price_unit': price_unit, 'discount': seller.discount or 0.0}
        else:
            po_line_uom = product_uom or self.product_id.uom_po_id
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                self.product_id.uom_id._compute_price(self.product_id.standard_price, po_line_uom),
                self.product_id.supplier_taxes_id,
                tax_ids,
                self.company_id,
            )
            price_unit = self.product_id.cost_currency_id._convert(
                price_unit, self.currency_id, self.company_id, fields.Date.today(), False
            )
            price_unit = float_round(
                price_unit,
                precision_digits=max(
                    self.currency_id.decimal_places,
                    self.env['decimal.precision'].precision_get('Product Price'),
                ),
            )
            return {'price_unit': price_unit, 'discount': 0.0}

    def _set_sale_product_data(self):
        """Set product data for sale subscriptions using recurring pricing."""
        self.ensure_one()
        if not self.product_id:
            return

        self.name = self.product_id.get_product_multiline_description_sale()
        self.product_uom_id = self.product_id.uom_id

        plan = self.subscription_id.plan_id
        pricelist = self.subscription_id.pricelist_id

        if plan:
            pricing = self.env['solt.recurring.pricing']._get_first_suitable_recurring_pricing(
                self.product_id, plan, pricelist
            )
            if pricing:
                self.price_unit = pricing.currency_id._convert(
                    pricing.price,
                    self.currency_id,
                    self.company_id,
                    fields.Date.today(),
                )
            else:
                self.price_unit = self.product_id.lst_price

        self.tax_ids = self.product_id.taxes_id.filtered(lambda tax: tax.company_id == self.company_id)

    def _prepare_invoice_line(self):
        """Prepare invoice line values for this subscription line."""
        self.ensure_one()

        subscription = self.subscription_id
        plan = subscription.plan_id

        # Calculate period dates
        period_start = subscription.next_invoice_date
        period_end = period_start + plan.billing_period - timedelta(days=1)

        # Format description with period
        description = self.name
        if plan:
            format_start = fields.Date.to_string(period_start)
            format_end = fields.Date.to_string(period_end)
            period_desc = f"\n{format_start} - {format_end}"
            description = f"{description} - {plan.billing_period_display}{period_desc}"

        return {
            'name': description,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom_id.id,
            'quantity': self.product_uom_qty,
            'price_unit': self.price_unit,
            'discount': self.discount,
            'tax_ids': [Command.set(self.tax_ids.ids)],
            'subscription_id': subscription.id,
            'analytic_distribution': self._get_analytic_distribution(),
        }

    @api.model
    def _get_price_from_pricing(self, product, plan, pricelist, currency, company):
        """Get the price for a product based on subscription pricing."""
        pricing = self.env['solt.recurring.pricing']._get_first_suitable_recurring_pricing(
            product, plan, pricelist
        )
        if pricing:
            return pricing.currency_id._convert(
                pricing.price,
                currency,
                company,
                fields.Date.today(),
            )
        return product.lst_price

    def _recalculate_price_for_plan(self, new_plan, old_plan):
        """Recalculate price_unit when switching plans.

        Strategy:
        1. Try to find explicit pricing in solt.recurring.pricing for the new plan.
        2. If no pricing found, calculate proportionally using INTERVAL_FACTOR
           (e.g. monthly $100 → annual $1,200 and vice versa).

        :param new_plan: solt.recurring.plan - the target plan
        :param old_plan: solt.recurring.plan - the source plan
        """
        self.ensure_one()
        pricing = self.env['solt.recurring.pricing']._get_first_suitable_recurring_pricing(
            self.product_id, new_plan, self.subscription_id.pricelist_id
        )
        if pricing:
            self.price_unit = pricing.currency_id._convert(
                pricing.price, self.currency_id, self.company_id, fields.Date.today()
            )
        else:
            old_monthly_factor = INTERVAL_FACTOR.get(old_plan.billing_period_unit, 1.0) / old_plan.billing_period_value
            new_monthly_factor = INTERVAL_FACTOR.get(new_plan.billing_period_unit, 1.0) / new_plan.billing_period_value
            self.price_unit = self.price_unit * old_monthly_factor / new_monthly_factor

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        company = self.subscription_id.company_id or self.env.company
        base_values = {
            'tax_ids': self.tax_ids,
            'quantity': self.product_uom_qty,
            'partner_id': self.subscription_id.partner_id,
            'currency_id': self.subscription_id.currency_id or company.currency_id,
            'rate': self.currency_rate,
            'name': self.name,
        }
        # if self._is_global_discount():
        #     base_values['special_type'] = 'global_discount'
        # elif self.is_downpayment:
        #     base_values['special_type'] = 'down_payment'
        base_values.update(kwargs)
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(self, **base_values)
