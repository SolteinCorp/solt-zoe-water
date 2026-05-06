# -*- coding: utf-8 -*-
# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class SoltSubscriptionRenewWizardLine(models.TransientModel):
    _name = 'solt.subscription.renew.wizard.line'
    _description = 'Subscription Wizard Line'

    wizard_id = fields.Many2one(
        'solt.subscription.renew.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
        help='Parent wizard that owns this line.',
    )
    line_type = fields.Selection(
        [('upsell', 'Upsell'), ('service_change', 'Service Change')],
        string='Line Type',
        required=True,
        default='upsell',
        help='Determines whether this line is an upsell addition or part of a service change.',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        help='Product to add or include in the new service set.',
    )
    product_uom_qty = fields.Float(
        string='Quantity',
        default=1.0,
        required=True,
        help='Quantity of the product.',
    )
    price_unit = fields.Float(
        string='Unit Price',
        digits='Product Price',
        help='Leave empty to auto-resolve from recurring pricing or product list price.',
    )
    name = fields.Text(
        string='Description',
        help='Leave empty to use the product default description.',
    )


class SoltSubscriptionRenewWizard(models.TransientModel):
    _name = "solt.subscription.renew.wizard"
    _description = 'Subscription Renew/Change Plan Wizard'

    subscription_id = fields.Many2one(
        'solt.subscription',
        string='Subscription',
        required=True,
        default=lambda self: self.env.context.get('active_id'),
        help='The subscription to renew/change',
    )
    action_type = fields.Selection([
        ('renew', 'Renew Subscription'),
        ('change_plan', 'Change Plan'),
        ('service_change', 'Change Services'),
        ('upsell', 'Add Products'),
    ], string='Action', required=True, default='renew',
        help='Select the type of change to apply to the subscription.')

    # Current subscription info (readonly)
    current_plan_id = fields.Many2one(
        'solt.recurring.plan',
        related='subscription_id.plan_id',
        string='Current Plan',
        help='The current recurring plan associated with this subscription (read-only).',
    )

    # For change_plan action
    new_plan_id = fields.Many2one(
        'solt.recurring.plan',
        string='New Plan',
        help='Select the new plan to switch to',
    )
    available_plan_ids_domain = fields.Binary(
        string="Available Plans Domain",
        compute="_compute_available_plan_ids_domain",
        compute_sudo=True,
        help='Domain filter for available plans that can be selected',
    )

    # For renew action
    extend_months = fields.Integer(
        string='Extend by (months)',
        default=12,
        help='Number of months to extend the subscription by',
    )

    # For upsell action
    upsell_line_ids = fields.One2many(
        'solt.subscription.renew.wizard.line',
        'wizard_id',
        string='Products to Add',
        domain=[('line_type', '=', 'upsell')],
        context={'default_line_type': 'upsell'},
        help='Products to add to the current subscription as an upsell.',
    )

    # For service_change action
    service_change_line_ids = fields.One2many(
        'solt.subscription.renew.wizard.line',
        'wizard_id',
        string='New Product Set',
        domain=[('line_type', '=', 'service_change')],
        context={'default_line_type': 'service_change'},
        help='Complete product set for the new subscription created by the service change.',
    )
    service_change_plan_id = fields.Many2one(
        'solt.recurring.plan',
        string='Plan for New Subscription',
        help='Leave empty to keep the same plan.',
    )

    @api.depends('subscription_id', 'subscription_id.plan_id')
    def _compute_available_plan_ids_domain(self):
        """Compute domain for available plans based on current plan's related plans."""
        for record in self:
            domain = [(0, '=', 1)]
            if record.subscription_id and record.subscription_id.plan_id:
                available_plans = record.subscription_id.available_plan_ids
                if available_plans:
                    domain = [('id', 'in', available_plans.ids)]
            record.available_plan_ids_domain = domain

    def action_confirm(self):
        """Execute the selected action."""
        self.ensure_one()

        action_handlers = {
            'change_plan': self._action_change_plan,
            'renew': self._action_renew,
            'upsell': self._action_upsell,
            'service_change': self._action_service_change,
        }
        handler = action_handlers.get(self.action_type)
        if handler:
            return handler()

    # === CHANGE PLAN === #

    def _action_change_plan(self):
        """Change plan: 1. Create new subscription 2. Calculate difference 3. Generate invoice 4. Activate on payment."""
        if not self.new_plan_id:
            raise UserError(_("Please select a new plan."))

        if self.new_plan_id == self.subscription_id.plan_id:
            raise UserError(_("The new plan must be different from the current plan."))

        if self.subscription_id.state != 'active':
            raise UserError(_("Plan can only be changed for active subscriptions. Current state: %s", self.subscription_id.state))

        subscription = self.subscription_id
        old_plan = subscription.plan_id
        today = fields.Date.today()

        subscription_lines = subscription.subscription_line_ids.filtered(
            lambda line: set(line.product_id.product_subscription_pricing_ids.plan_id.ids).intersection(
                set(subscription.available_plan_ids.ids)))

        # STEP 1: Create new subscription with new plan in DRAFT state
        new_subscription = subscription.sudo().copy({
            'plan_id': self.new_plan_id.id,
            'origin_subscription_id': subscription.id,
            'state': 'draft',
            'subscription_line_ids': [Command.create(sl.copy_data()[0]) for sl in subscription_lines],
        })
        new_subscription.subscription_line_ids._onchange_product_id()

        # Get the next invoice date (end of current billing period)
        current_end = subscription.next_invoice_date or today

        # Calculate days remaining
        days_remaining = max((current_end - today).days, 0)

        # Get period in days
        period_days_map = {
            'week': old_plan.billing_period_value * 7,
            'month': old_plan.billing_period_value * 30,
            'year': old_plan.billing_period_value * 365,
        }
        period_days = period_days_map.get(old_plan.billing_period_unit, old_plan.billing_period_value)

        # STEP 2: Calculate prorated difference for new subscription
        invoice_lines = []
        total_difference = 0

        if days_remaining > 0:
            for old_line in subscription.subscription_line_ids:
                new_line = new_subscription.subscription_line_ids.filtered(
                    lambda line, product=old_line.product_id: line.product_id == product)
                old_prorated = (days_remaining / period_days) * old_line.price_total if period_days > 0 else 0
                new_prorated = (days_remaining / period_days) * new_line.price_total if period_days > 0 else 0
                difference = new_prorated - old_prorated
                total_difference += difference
                if difference != 0:
                    invoice_lines.append({
                        'product_id': old_line.product_id.id,
                        'name': _('%s - Plan change adjustment (%s days)', old_line.product_id.name, days_remaining),
                        'quantity': old_line.product_uom_qty,
                        'price_unit': difference / old_line.product_uom_qty if old_line.product_uom_qty > 0 else difference,
                    })

        # STEP 3: Generate invoice or credit note for new subscription
        if total_difference > 0:
            invoice_vals = new_subscription._prepare_invoice()
            invoice_vals['invoice_line_ids'] = []
            invoice_vals['invoice_date'] = today

            for inv_line in invoice_lines:
                product = self.env['product.product'].browse(inv_line['product_id'])
                accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=subscription.fiscal_position_id)
                account_id = accounts.get('income') and accounts['income'].id

                invoice_vals['invoice_line_ids'].append(Command.create({
                    'product_id': inv_line['product_id'],
                    'name': inv_line['name'],
                    'quantity': inv_line['quantity'],
                    'price_unit': inv_line['price_unit'],
                    'account_id': account_id,
                    'subscription_id': new_subscription.id,
                }))

            if invoice_vals['invoice_line_ids']:
                prorated_invoice = self.env['account.move'].sudo().create(invoice_vals)
                prorated_invoice.action_post()
                new_subscription.message_post(body=_("Upgrade charge invoice: %s", prorated_invoice._get_html_link()))
                new_subscription.pending_transaction = True
                subscription.message_post(
                    body=_("Plan change requested to %s. New subscription: %s. Invoice to pay: %s",
                        self.new_plan_id.name,
                        new_subscription._get_html_link(),
                        prorated_invoice._get_html_link())
                )
            else:
                self._activate_plan_change(subscription, new_subscription)

        elif total_difference < 0:
            invoice_vals = new_subscription._prepare_invoice()
            invoice_vals['invoice_line_ids'] = []
            invoice_vals['invoice_date'] = today
            invoice_vals['move_type'] = 'out_refund'

            for inv_line in invoice_lines:
                if inv_line['price_unit'] < 0:
                    product = self.env['product.product'].browse(inv_line['product_id'])
                    accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=subscription.fiscal_position_id)
                    account_id = accounts.get('income') and accounts['income'].id

                    invoice_vals['invoice_line_ids'].append(Command.create({
                        'product_id': inv_line['product_id'],
                        'name': inv_line['name'],
                        'quantity': inv_line['quantity'],
                        'price_unit': abs(inv_line['price_unit']),
                        'account_id': account_id,
                        'subscription_id': new_subscription.id,
                    }))

            if invoice_vals['invoice_line_ids']:
                credit_invoice = self.env['account.move'].sudo().create(invoice_vals)
                credit_invoice.action_post()
                new_subscription.message_post(body=_("Downgrade credit note: %s", credit_invoice._get_html_link()))

            self._activate_plan_change(subscription, new_subscription)
            subscription.message_post(body=_("Plan downgraded to %s. New subscription active: %s", self.new_plan_id.name, new_subscription._get_html_link()))
            new_subscription.message_post(body=_("Activated from plan change. Previous subscription closed: %s", subscription._get_html_link()))

        else:
            self._activate_plan_change(subscription, new_subscription)
            subscription.message_post(
                body=_("Plan changed to %s. New subscription: %s",
                    self.new_plan_id.name,
                    new_subscription._get_html_link())
            )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'solt.subscription',
            'res_id': new_subscription.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _activate_plan_change(self, old_subscription, new_subscription):
        """Activate new subscription and close old one after a plan change."""
        new_subscription.sudo().action_confirm()
        old_subscription.sudo().set_close(close_reason_id=self.env.ref(
            'solt_recurring_payment.close_reason_plan_change',
            raise_if_not_found=False
        ).id or False)

    # === RENEW === #

    def _action_renew(self):
        """Renew the subscription: extend end date and reactivate if paused/closed."""
        if self.extend_months <= 0:
            raise UserError(_("Please enter a positive number of months."))

        subscription = self.subscription_id
        current_end = subscription.end_date or subscription.next_invoice_date
        if not current_end:
            current_end = fields.Date.today()

        new_end_date = current_end + relativedelta(months=self.extend_months)

        subscription_sudo = subscription.sudo()
        subscription_sudo.end_date = new_end_date

        if subscription.state == 'closed':
            subscription_sudo.set_open()
            subscription.message_post(
                body=_("Subscription renewed and reopened. Extended by %d months. New end date: %s",
                    self.extend_months, new_end_date)
            )
        else:
            subscription.message_post(
                body=_("Subscription extended by %d months. New end date: %s",
                    self.extend_months, new_end_date)
            )

        return {'type': 'ir.actions.act_window_close'}

    # === UPSELL === #

    def _action_upsell(self):
        """Add new product lines to the active subscription with proration."""
        if self.subscription_id.state != 'active':
            raise UserError(_("Upsell is only available for active subscriptions."))
        if not self.upsell_line_ids:
            raise UserError(_("Please add at least one product to upsell."))

        self.subscription_id.sudo()._upsell_add_lines(self.upsell_line_ids)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'solt.subscription',
            'res_id': self.subscription_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # === SERVICE CHANGE === #

    def _action_service_change(self):
        """Create new subscription with different products, closing the current one."""
        if self.subscription_id.state != 'active':
            raise UserError(_("Service change is only available for active subscriptions."))
        if not self.service_change_line_ids:
            raise UserError(_("Please define the new product set."))

        subscription = self.subscription_id
        target_plan = self.service_change_plan_id or subscription.plan_id

        # Create new subscription in draft with the new product set
        new_subscription = subscription.sudo().copy({
            'plan_id': target_plan.id,
            'origin_subscription_id': subscription.id,
            'state': 'draft',
            'start_date': fields.Date.today(),
            'subscription_line_ids': [],
        })

        # Create lines from wizard selection
        for wizard_line in self.service_change_line_ids:
            resolved_price = wizard_line.price_unit
            if not resolved_price:
                resolved_price = self.env['solt.subscription.line']._get_price_from_pricing(
                    wizard_line.product_id, target_plan, subscription.pricelist_id,
                    subscription.currency_id, subscription.company_id,
                )

            product_taxes = wizard_line.product_id.taxes_id.filtered(
                lambda tax: tax.company_id == subscription.company_id
            )

            self.env['solt.subscription.line'].create({
                'subscription_id': new_subscription.id,
                'product_id': wizard_line.product_id.id,
                'name': wizard_line.name or wizard_line.product_id.get_product_multiline_description_sale(),
                'product_uom_qty': wizard_line.product_uom_qty,
                'price_unit': resolved_price,
                'product_uom_id': wizard_line.product_id.uom_id.id,
                'tax_ids': [Command.set(product_taxes.ids)],
            })

        # Prepare and execute service change (hook for integration modules)
        service_change_data = subscription._prepare_service_change_data(new_subscription)
        subscription._execute_service_change(service_change_data)

        # Generate credit note for unused period on old subscription
        subscription.sudo()._create_unused_period_credit_note()

        # Activate new subscription and close old one
        new_subscription.sudo().action_confirm()
        subscription.sudo().set_close(
            close_reason_id=self.env.ref(
                'solt_recurring_payment.close_reason_plan_change',
                raise_if_not_found=False,
            ).id or False,
        )

        subscription.message_post(body=_(
            "Service change completed. New subscription: %s",
            new_subscription._get_html_link(),
        ))
        new_subscription.message_post(body=_(
            "Created from service change. Previous subscription: %s",
            subscription._get_html_link(),
        ))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'solt.subscription',
            'res_id': new_subscription.id,
            'view_mode': 'form',
            'target': 'current',
        }
