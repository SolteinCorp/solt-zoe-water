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
    _inherit = 'analytic.mixin'
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
    product_domain = fields.Char(
        string='Product Domain',
        compute='_compute_product_domain',
        help='Domain to filter products based on the subscription type.',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain="product_domain",
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
    free_periods = fields.Integer(
        string='Free Periods',
        default=0,
        copy=False,
        help='Number of free periods at the start of the subscription for this line. '
             'Each unit is a full plan period (e.g. 1 = one full year free on an annual plan). '
             'While start_date + free_periods * period > today, the line is skipped from invoices '
             'and only starts billing once the free window has elapsed.',
    )
    is_downpayment = fields.Boolean(
        string='Is Downpayment',
        default=False,
        copy=False,
        help='Marks this line as a downpayment. Mirrors the sale.advance.payment.inv wizard '
             'semantics: the line represents N prepaid periods. The first invoice charges '
             'qty=product_uom_qty (full prepaid quantity); each subsequent monthly invoice '
             'includes a negative qty=-period_qty counterpart until the balance is exhausted.',
    )
    period_qty = fields.Float(
        string='Quantity per Period',
        default=1.0,
        copy=False,
        help='Quantity consumed per billing period when this line is a downpayment. '
             'The prepaid invoice posts product_uom_qty (= period_qty * number of prepaid '
             'periods); each monthly invoice applies qty=-period_qty.',
    )
    initial_invoice_done = fields.Boolean(
        string='Initial Invoice Issued',
        default=False,
        copy=False,
        help='True once the initial prepaid invoice has been issued. When qty_invoiced '
             'returns to 0 (advance fully consumed), this line stops generating new prepaid '
             'invoices and the subscription continues with regular billing.',
    )
    qty_invoiced = fields.Float(
        string='Quantity Invoiced',
        default=0.0,
        copy=False,
        help='Cumulative invoiced quantity for this line (positives add, negatives subtract). '
             'For downpayment lines it tracks how many prepaid periods are still pending '
             'application against monthly invoices.',
    )
    qty_to_invoice = fields.Float(
        string='Quantity to Invoice',
        compute='_compute_qty_to_invoice',
        help='For downpayment lines: the positive qty (initial invoice) when not yet invoiced, '
             'or the remaining negative qty (monthly applications) while there is balance.',
    )

    @api.depends('product_uom_qty', 'qty_invoiced', 'is_downpayment')
    def _compute_qty_to_invoice(self):
        for line in self:
            if line.is_downpayment:
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = line.product_uom_qty
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
        domain="[('category_id', '=', product_uom_category_id)]",
        help='Unit of measure for the product.',
    )
    product_uom_category_id = fields.Many2one(
        string='Category of UOM',
        related='product_id.uom_id.category_id',
        help='UoM category related to the selected product.',
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

    @api.depends('subscription_type')
    def _compute_product_domain(self):
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
        if not self.product_id:
            return

        if self.subscription_type == 'purchase':
            self._set_purchase_product_data()
        else:
            self._set_sale_product_data()

    def _set_purchase_product_data(self):
        """Set product data for purchase subscriptions."""
        self.ensure_one()
        if not self.product_id:
            return

        # Set description and UoM for purchase
        self.name = self.product_id.display_name
        if self.product_id.description_purchase:
            self.name += '\n' + self.product_id.description_purchase
        self.product_uom_id = self.product_id.uom_po_id or self.product_id.uom_id

        # Set default taxes for purchase
        self.tax_ids = self.product_id.supplier_taxes_id.filtered(
            lambda t: t.company_id == self.company_id
        )

        # Get price from vendor/seller
        price_data = self._get_purchase_price_data()
        self.price_unit = price_data['price_unit']
        self.discount = price_data.get('discount', 0.0)

    def _get_purchase_price_data(self):
        """
        Get price data for purchase subscriptions from vendor/seller.
        Returns a dict with 'price_unit' and 'discount'.
        This method is reusable for invoice line preparation.
        """
        self.ensure_one()
        if not self.product_id:
            return {'price_unit': 0.0, 'discount': 0.0}

        plan = self.subscription_id.plan_id
        partner = self.subscription_id.partner_id

        if not plan:
            return {'price_unit': self.product_id.standard_price, 'discount': 0.0}

        # Use existing product_uom or fallback to product defaults
        product_uom = self.product_uom_id
        if not product_uom:
            product_uom = self.product_id.uom_po_id if self.product_id.uom_po_id.id else self.product_id.uom_id
        # Use existing tax_ids or fallback to supplier taxes
        tax_ids = self.tax_ids or self.product_id.supplier_taxes_id.filtered(
            lambda t: t.company_id == self.company_id
        )

        # Select seller filtering by partner
        seller = self.product_id._select_seller(
            partner_id=partner,
            quantity=self.product_uom_qty,
            date=fields.Date.today(),
            uom_id=product_uom,
        )

        if seller:
            # Use seller price with tax and currency conversion
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                seller.price,
                self.product_id.supplier_taxes_id,
                tax_ids,
                self.company_id
            )
            price_unit = seller.currency_id._convert(
                price_unit,
                self.currency_id,
                self.company_id,
                fields.Date.today(),
                False
            )
            price_unit = float_round(
                price_unit,
                precision_digits=max(
                    self.currency_id.decimal_places,
                    self.env['decimal.precision'].precision_get('Product Price')
                )
            )
            price_unit = seller.product_uom._compute_price(price_unit, product_uom)
            return {'price_unit': price_unit, 'discount': seller.discount or 0.0}
        else:
            # Fallback to standard price if no seller found
            po_line_uom = product_uom or self.product_id.uom_po_id
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                self.product_id.uom_id._compute_price(self.product_id.standard_price, po_line_uom),
                self.product_id.supplier_taxes_id,
                tax_ids,
                self.company_id,
            )
            price_unit = self.product_id.cost_currency_id._convert(
                price_unit,
                self.currency_id,
                self.company_id,
                fields.Date.today(),
                False
            )
            price_unit = float_round(
                price_unit,
                precision_digits=max(
                    self.currency_id.decimal_places,
                    self.env['decimal.precision'].precision_get('Product Price')
                )
            )
            return {'price_unit': price_unit, 'discount': 0.0}

    def _set_sale_product_data(self):
        """Set product data for sale subscriptions."""
        self.ensure_one()
        if not self.product_id:
            return

        # Set description and UoM for sale
        self.name = self.product_id.get_product_multiline_description_sale()
        self.product_uom = self.product_id.uom_id

        # Set default taxes for sale
        self.tax_ids = self.product_id.taxes_id.filtered(
            lambda t: t.company_id == self.company_id
        )

        # Get price from subscription pricing
        self.price_unit = self._get_sale_price_data()

    def _get_sale_price_data(self):
        """
        Get price for sale subscriptions from solt.recurring.pricing.
        Returns the price_unit value.
        This method is reusable for invoice line preparation.
        """
        self.ensure_one()
        if not self.product_id:
            return 0.0

        plan = self.subscription_id.plan_id
        pricelist = self.subscription_id.pricelist_id

        if plan:
            Pricing = self.env['solt.recurring.pricing']
            pricing = Pricing._get_first_suitable_recurring_pricing(self.product_id, plan)
            if pricing:
                base_price = pricing.currency_id._convert(
                    pricing.price,
                    self.currency_id,
                    self.company_id,
                    fields.Date.today(),
                )
                return Pricing._apply_pricelist_rule(
                    base_price, pricelist, self.product_id, plan,
                    self.product_uom_qty or 1.0, self.product_uom_id,
                    fields.Date.today(), currency=self.currency_id,
                )
        # Fallback to product price
        return self.product_id.lst_price

    def _prepare_invoice_line(self, quantity=None):
        """Prepare invoice line values for this subscription line.

        :param quantity: optional override for the line quantity. Used by
            ``solt.subscription._create_invoices`` to emit downpayment lines
            (positive on the initial prepaid invoice, negative on subsequent
            monthly invoices).
        """
        self.ensure_one()

        subscription = self.subscription_id
        plan = subscription.plan_id

        # Calculate period dates
        period_start = subscription.next_invoice_date
        period_end = period_start + plan.billing_period - timedelta(days=1)

        # Format description with period
        description = self.name
        if plan and not self.is_downpayment:
            format_start = fields.Date.to_string(period_start)
            format_end = fields.Date.to_string(period_end)
            period_desc = f"\n{format_start} - {format_end}"
            description = f"{description} - {plan.billing_period_display}{period_desc}"

        # For purchase subscriptions, recalculate price from vendor (may have changed)
        if self.subscription_type == 'purchase':
            price_data = self._get_purchase_price_data()
            price_unit = price_data['price_unit']
            discount = price_data.get('discount', 0.0)
        else:
            price_unit = self.price_unit
            discount = self.discount

        return {
            'name': description,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom_id.id,
            'quantity': self.product_uom_qty if quantity is None else quantity,
            'price_unit': price_unit,
            'discount': discount,
            'tax_ids': [Command.set(self.tax_ids.ids)],
            'subscription_id': subscription.id,
            'is_downpayment': self.is_downpayment,
        }

    @api.model
    def _get_price_from_pricing(self, product, plan, pricelist, currency, company):
        """Get the price for a product based on subscription pricing."""
        Pricing = self.env['solt.recurring.pricing']
        pricing = Pricing._get_first_suitable_recurring_pricing(product, plan)
        if pricing:
            base_price = pricing.currency_id._convert(
                pricing.price,
                currency,
                company,
                fields.Date.today(),
            )
            return Pricing._apply_pricelist_rule(
                base_price, pricelist, product, plan,
                1.0, product.uom_id, fields.Date.today(), currency=currency,
            )
        return product.lst_price

    def _recalculate_price_for_plan(self, new_plan, old_plan):
        """Recalculate price_unit when switching plans.

        Strategy:
        1. Try to find explicit pricing in solt.recurring.pricing for the new plan.
        2. If no pricing found, calculate proportionally using INTERVAL_FACTOR
           (e.g. monthly $100 → annual $1,200 and vice versa).

        Args:
            new_plan: solt.recurring.plan - the target plan
            old_plan: solt.recurring.plan - the source plan
        """
        self.ensure_one()
        Pricing = self.env['solt.recurring.pricing']
        pricing = Pricing._get_first_suitable_recurring_pricing(self.product_id, new_plan)
        if pricing:
            base_price = pricing.currency_id._convert(
                pricing.price, self.currency_id, self.company_id, fields.Date.today(),
            )
            self.price_unit = Pricing._apply_pricelist_rule(
                base_price, self.subscription_id.pricelist_id,
                self.product_id, new_plan,
                self.product_uom_qty or 1.0, self.product_uom_id,
                fields.Date.today(), currency=self.currency_id,
            )
        else:
            # Proportional fallback: normalize to monthly then convert to new period
            old_monthly_factor = INTERVAL_FACTOR.get(old_plan.billing_period_unit, 1.0) / old_plan.billing_period_value
            new_monthly_factor = INTERVAL_FACTOR.get(new_plan.billing_period_unit, 1.0) / new_plan.billing_period_value
            self.price_unit = self.price_unit * old_monthly_factor / new_monthly_factor

    def _prepare_base_line_for_taxes_computation(self, **kwargs):
        """Convert the current record to a base line dict for the generic taxes computation."""
        self.ensure_one()
        company = self.subscription_id.company_id or self.env.company
        base_values = {
            'tax_ids': self.tax_ids,
            'quantity': self.product_uom_qty,
            'partner_id': self.subscription_id.partner_id,
            'currency_id': self.subscription_id.currency_id or company.currency_id,
        }
        base_values.update(kwargs)
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(self, **base_values)
