# -*- coding: utf-8 -*-
import logging
import traceback
from collections import defaultdict

from dateutil.relativedelta import relativedelta
from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.osv import expression
from odoo.tools import config, plaintext2html, split_every, str2bool
from psycopg2._psycopg import TransactionRollbackError

_logger = logging.getLogger(__name__)

SUBSCRIPTION_STATES = [('draft', 'Draft'), ('active', 'Active'), ('closed', 'Closed')]

SUBSCRIPTION_DRAFT_STATE = ['draft']
SUBSCRIPTION_ACTIVE_STATE = ['active']
SUBSCRIPTION_CLOSED_STATE = ['closed']


class SoltSaleSubscription(models.Model):
    _name = 'solt.subscription'
    _description = 'Subscription'
    _inherit = ['mail.activity.mixin', 'rating.mixin', 'portal.mixin']
    _order = 'id desc'
    _check_company_auto = True

    # === BASIC FIELDS === #
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
        help="Unique reference for the subscription, generated automatically."
    )
    type = fields.Selection(
        [('sale', 'Sale'), ('purchase', 'Purchase')],
        string='Type',
        required=True,
        default='sale',
        help="Type of the subscription: Sale or Purchase."
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
        help="The company this subscription belongs to."
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        check_company=True,
        help="The customer associated with this subscription."
    )
    commercial_partner_id = fields.Many2one(
        'res.partner',
        related='partner_id.commercial_partner_id',
        store=True,
        readonly=True,
        precompute=True,
        string='Commercial Partner',
        help="The commercial entity related to the customer."
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True,
        help="Currency used for this subscription."
    )
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
        check_company=True,
        tracking=True,
        help="Pricelist used to compute product prices for this subscription."
    )
    plan_id = fields.Many2one(
        'solt.recurring.plan',
        string='Recurring Plan',
        required=True,
        tracking=True,
        help="The recurring plan that defines the billing cycle and rules."
    )
    origin_id = fields.Reference(
        [('sale.order', 'Sale Order'), ('purchase.order', 'Purchase Order')],
        string='Origin Document',
        readonly=True,
        copy=False,
        help="The original document from which this subscription was created."
    )
    user_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        default=lambda self: self.env.user,
        tracking=True,
        help="The salesperson responsible for this subscription."
    )
    # === STATE FIELDS === #
    state = fields.Selection(
        selection=SUBSCRIPTION_STATES,
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        group_expand='_group_expand_states',
        index=True,
        help="Current status of the subscription: Draft, Active, or Closed."
    )
    start_date = fields.Date(
        string='Start Date',
        tracking=True,
        help="The date when the subscription becomes active."
    )
    next_invoice_date = fields.Date(
        string='Next Invoice Date',
        tracking=True,
        copy=False,
        help="The scheduled date for the next invoice to be generated for this subscription."
    )
    end_date = fields.Date(
        string='End Date',
        tracking=True,
        help="The date when the subscription will be closed. Leave empty for ongoing subscriptions."
    )
    close_reason_id = fields.Many2one(
        'solt.subscription.close.reason',
        string='Close Reason',
        tracking=True,
        copy=False,
        help="The reason for closing the subscription, if applicable."
    )
    close_date = fields.Date(
        string='Close Date',
        tracking=True,
        copy=False,
        help="The date when the subscription was actually closed.",
    )
    active = fields.Boolean(
        default=True,
        tracking=True,
        help="When unchecked, the subscription is archived and hidden from default views.",
    )

    # === LINES === #
    subscription_line_ids = fields.One2many(
        'solt.subscription.line',
        'subscription_id',
        string='Subscription Lines',
        copy=True,
        help="The lines that define the products and services included in this subscription."
    )

    # === PAYMENT FIELDS === #
    payment_token_id = fields.Many2one('payment.token', string='Payment Token', check_company=True, domain="[('partner_id', 'child_of', commercial_partner_id), ('company_id', '=', company_id)]", copy=True,
        help="If set, automatic payments will use this token.",
    )
    payment_exception = fields.Boolean(string='Payment Exception', copy=False, help="Indicates that the last automatic payment failed.")
    pending_transaction = fields.Boolean(string='Pending Transaction', copy=False, help="Indicates that there is a pending payment transaction.")
    # === COMPUTED AMOUNTS === #
    recurring_total = fields.Monetary(
        string='Recurring Total',
        compute='_compute_recurring_total',
        store=True,
        tracking=True,
        help="Total recurring amount for the subscription, based on the current plan and lines."
    )
    recurring_monthly = fields.Monetary(
        string='Monthly Recurring Revenue',
        compute='_compute_recurring_monthly',
        store=True,
        tracking=True,
        help="Monthly recurring revenue (MRR) calculated from the subscription lines. Only set when the subscription is active."
    )
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_amounts',
        store=True,
        help="Total amount for the subscription before taxes."
    )
    amount_tax = fields.Monetary(
        string='Taxes',
        compute='_compute_amounts',
        store=True,
        help="Total tax amount for the subscription."
    )
    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amounts',
        store=True,
        help="Total amount for the subscription, including taxes."
    )
    tax_totals = fields.Binary(
        string='Tax Total',
        compute='_compute_tax_totals',
        exportable=False,
        help='Serialized tax totals for the subscription, used for reporting and invoicing purposes.',
    )

    # === INVOICING === #
    invoice_ids = fields.Many2many(
        'account.move',
        compute='_compute_invoice_count',
        string='Invoices',
        store=True,
        readonly=True,
        copy=False,
        help="Invoices generated for this subscription."
    )
    invoice_line_ids = fields.One2many(
        'account.move.line',
        'subscription_id',
        string='Invoices Lines',
        store=True,
        readonly=True,
        copy=False,
        help="Invoice lines related to this subscription."
    )
    invoice_count = fields.Integer(
        string='Invoice Count',
        store=True,
        readonly=True,
        compute='_compute_invoice_count',
        copy=False,
        help="Number of invoices generated for this subscription."
    )

    # === RENEWAL === #
    origin_subscription_id = fields.Many2one('solt.subscription', string='Origin Subscription', readonly=True, copy=False, help="The subscription this one was renewed from.")
    renewed_subscription_ids = fields.One2many('solt.subscription', 'origin_subscription_id', string='Renewed Subscription', readonly=True, copy=False, help="The subscription that renewed this one.")
    # === PORTAL FIELDS === #
    user_closable = fields.Boolean(
        string='Closable',
        related='plan_id.user_closable',
        help="Indicates if the user is allowed to close the subscription according to the plan settings."
    )
    user_extend = fields.Boolean(
        string='Extendable',
        related='plan_id.user_extend',
        help="Indicates if the user is allowed to extend the subscription according to the plan settings."
    )

    # === NOTES === #
    internal_note = fields.Html(string='Internal Notes',
        help="Internal notes for the subscription, visible only to staff users.")
    description = fields.Text(string='Description',
        help="Public description of the subscription, visible to the customer.")

    # === UI/UX === #
    display_late = fields.Boolean(
        string='Display Late',
        compute='_compute_display_late',
        help="Indicates if the subscription is late for its next invoice."
    )
    percentage_satisfaction = fields.Integer(
        compute='_compute_percentage_satisfaction',
        string='% Satisfaction',
        store=True,
        default=-1,
        help="Customer satisfaction percentage based on received ratings."
    )
    is_batch = fields.Boolean(
        string='Is Batch',
        default=False,
        copy=False,
        help="Technical flag: True if this subscription is part of a batch of invoices processed together."
    )
    # technical flag to avoid process the same subscription in several parallel crons
    is_invoice_cron = fields.Boolean(
        string='Is a Subscription invoiced in cron',
        default=False,
        copy=False,
        help="Technical flag: True if this subscription is being invoiced by a scheduled cron job."
    )
    fiscal_position_id = fields.Many2one('account.fiscal.position', string="Fiscal Position", compute='_compute_fiscal_position_id', store=True, readonly=False, precompute=True, check_company=True,
        help="Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices.The default value comes from the customer.",
    )
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string="Payment Terms",
        compute='_compute_payment_term_id',
        store=True,
        readonly=False,
        precompute=True,
        check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="The payment terms that apply to this subscription. Determines the due date for invoices. Defaults to the customer's payment terms."
    )
    journal_id = fields.Many2one('account.journal', string="Invoicing Journal", domain=[('type', '=', 'sale')], check_company=True,
        help="If set, the SO will invoice in this journal; otherwise the sales journal with the lowest sequence is used.",
    )
    available_plan_ids = fields.Many2many(
        'solt.recurring.plan',
        string="Available Plans Domain",
        compute="_compute_available_plan_ids",
        compute_sudo=True,
        help="List of recurring plans available for the current subscription lines and products. Used to restrict selectable plans based on product compatibility."
    )

    # === SQL CONSTRAINTS === #
    _sql_constraints = [
        ('check_start_date_lower_next_invoice_date', 'CHECK((next_invoice_date IS NULL OR start_date IS NULL) OR (next_invoice_date >= start_date))', 'The next invoice date should be after the start date.'),
    ]

    @api.depends('plan_id', 'subscription_line_ids.product_id.product_subscription_pricing_ids')
    def _compute_available_plan_ids(self):
        for record in self:
            record.available_plan_ids = record.subscription_line_ids.product_id.product_subscription_pricing_ids.filtered(lambda p, rp=record.plan_id.related_plan_ids.ids: p.plan_id.id in rp).plan_id.ids

    @api.depends('commercial_partner_id', 'partner_id', 'company_id')
    def _compute_fiscal_position_id(self):
        """
        Trigger the change of fiscal position when the shipping address is modified.
        """
        cache = {}
        for order in self:
            if not order.partner_id:
                order.fiscal_position_id = False
                continue
            key = (order.company_id.id, order.partner_id.id, order.commercial_partner_id.id)
            if key not in cache:
                cache[key] = self.env['account.fiscal.position'].with_company(order.company_id)._get_fiscal_position(order.partner_id, order.commercial_partner_id).id
            order.fiscal_position_id = cache[key]

    @api.depends('partner_id')
    def _compute_payment_term_id(self):
        for order in self:
            order = order.with_company(order.company_id)
            order.payment_term_id = order.partner_id.property_payment_term_id

    @api.depends('subscription_line_ids.price_subtotal')
    def _compute_amounts(self):
        """Compute untaxed, tax, and total amounts from subscription lines."""
        for subscription in self:
            lines = subscription.subscription_line_ids
            subscription.amount_untaxed = sum(lines.mapped('price_subtotal'))
            subscription.amount_tax = sum(lines.mapped('price_tax'))
            subscription.amount_total = sum(lines.mapped('price_total'))

    @api.depends_context("lang")
    @api.depends("subscription_line_ids.tax_ids", "subscription_line_ids.price_subtotal", "amount_total", "amount_untaxed")
    def _compute_tax_totals(self):
        """Compute the serialized tax totals for the subscription."""
        for subscription in self:
            AccountTax = self.env["account.tax"]
            order_lines = subscription.subscription_line_ids
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, subscription.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, subscription.company_id)
            subscription.tax_totals = AccountTax._get_tax_totals_summary(base_lines=base_lines, currency=subscription.currency_id or subscription.company_id.currency_id, company=subscription.company_id, )

    @api.depends('subscription_line_ids.price_subtotal')
    def _compute_recurring_total(self):
        for subscription in self:
            subscription.recurring_total = sum(subscription.subscription_line_ids.mapped('price_subtotal'))

    @api.depends('subscription_line_ids.recurring_monthly', 'state')
    def _compute_recurring_monthly(self):
        for subscription in self:
            if subscription.state in SUBSCRIPTION_ACTIVE_STATE:
                subscription.recurring_monthly = sum(subscription.subscription_line_ids.mapped('recurring_monthly'))
            else:
                subscription.recurring_monthly = 0

    @api.depends('subscription_line_ids', 'invoice_line_ids')
    def _compute_invoice_count(self):
        invoices = self.env['account.move.line'].read_group([('subscription_id', 'in', self.ids)], ['subscription_id', 'move_id:array_agg'], ['subscription_id', 'move_id'], lazy=False)
        invoice_map = defaultdict(lambda: {'move_id': [], 'move_id_count': 0})
        for data in invoices:
            sub_id = data['subscription_id'][0]
            invoice_map[sub_id]['move_id'] += [data['move_id'][0]] if data['move_id'] else []
            invoice_map[sub_id]['move_id_count'] += 1 if data['__count'] else 0
        for subscription in self:
            data = invoice_map.get(subscription.id, {'move_id': [], 'move_id_count': 0})
            subscription.invoice_ids = data['move_id']
            subscription.invoice_count = data['move_id_count']

    @api.depends('state', 'next_invoice_date')
    def _compute_display_late(self):
        today = fields.Date.today()
        for subscription in self:
            subscription.display_late = subscription.state in SUBSCRIPTION_ACTIVE_STATE and subscription.next_invoice_date and subscription.next_invoice_date < today

    @api.depends('rating_percentage_satisfaction')
    def _compute_percentage_satisfaction(self):
        for subscription in self:
            subscription.percentage_satisfaction = int(subscription.rating_percentage_satisfaction)

    def _compute_access_url(self):
        for subscription in self:
            subscription.access_url = f'/my/subscriptions/{subscription.id}'
        return

    def _group_expand_states(self, states, domain, order):
        return ['active']

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        """
        Create new subscription records.

        If the 'name' field is set to the default value, it assigns a new sequence value.
        :param vals_list: List of dictionaries with values for new records.
        :return: Recordset of created subscriptions.
        """
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('solt.subscription') or _('New')
        subscriptions = super().create(vals_list)
        return subscriptions

    def copy(self, default=None):
        """
        Duplicate the subscription record.

        Sets the state to 'draft', clears start and next invoice dates, and sets the origin subscription.
        :param default: Optional dictionary of default values for the copy.
        :return: The duplicated subscription record.
        """
        default = dict(default or {})
        default.update({'state': 'draft', 'start_date': False, 'next_invoice_date': False, 'origin_subscription_id': self.id})
        return super().copy(default)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        """Prevent deletion unless the subscription is in draft or closed and archived."""
        for subscription in self:
            if subscription.state == 'draft':
                continue
            if subscription.state == 'closed' and not subscription.active:
                continue
            raise UserError(_(
                "You can only delete subscriptions that are in draft or closed and archived. "
                "Subscription '%s' is in state '%s'%s.",
                subscription.name,
                subscription.state,
                _(" (not archived)") if subscription.state == 'closed' and subscription.active else "",
            ))

    def write(self, vals):
        """Override write to enforce archiving rules: only closed subscriptions can be archived."""
        if 'active' in vals and not vals['active']:
            non_archivable = self.filtered(lambda sub: sub.state != 'closed')
            if non_archivable:
                raise UserError(_(
                    "Only closed subscriptions can be archived. "
                    "The following subscriptions are not closed: %s",
                    ', '.join(non_archivable.mapped('name')),
                ))
        previously_active = (
            self.filtered(lambda sub: sub.active)
            if 'active' in vals and not vals['active']
            else self.env['solt.subscription']
        )
        result = super().write(vals)
        if previously_active:
            previously_active._post_archived()
        return result

    # === ACTION METHODS === #

    def action_confirm(self):
        """Confirm the subscription, set it to active, and trigger the post-activate hook."""
        today = fields.Date.today()
        for subscription in self:
            if subscription.state != 'draft':
                continue
            if not subscription.subscription_line_ids:
                raise UserError(_("You cannot confirm a subscription without lines."))
            if not subscription.start_date:
                subscription.start_date = today
            if not subscription.next_invoice_date:
                subscription.next_invoice_date = subscription.start_date
            else:
                # Adjust next_invoice_date relative to the actual first payment
                # date (today) instead of the original order date (start_date).
                first_payment_offset = today - subscription.start_date
                if first_payment_offset.days > 0:
                    subscription.next_invoice_date += first_payment_offset
            subscription.state = 'active'
            subscription._portal_ensure_token()
            subscription._post_activate()
        return True

    def set_close(self, close_reason_id=None):
        """Close the subscription, record the close date, and trigger the post-close hook."""
        today = fields.Date.today()
        for subscription in self:
            if subscription.state not in SUBSCRIPTION_ACTIVE_STATE:
                raise UserError(_("Only active subscriptions can be closed."))
            close_vals = {'state': 'closed', 'close_date': today}
            if close_reason_id:
                close_vals['close_reason_id'] = close_reason_id
            subscription.write(close_vals)
            subscription._post_close()
        return True

    def action_reopen(self):
        """Reopen a closed subscription back to active state and trigger the post-activate hook."""
        today = fields.Date.today()
        for subscription in self:
            if subscription.state != 'closed':
                raise UserError(_("Only closed subscriptions can be reopened."))
            subscription.write({
                'state': 'active',
                'close_reason_id': False,
                'close_date': False,
                'active': True,
                'next_invoice_date': today,
            })
            subscription._post_activate()
        return True

    def action_open_close_wizard(self):
        """Open the close subscription wizard."""
        self.ensure_one()
        return {
            'name': _('Close Subscription'),
            'type': 'ir.actions.act_window',
            'res_model': 'solt.subscription.close.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_subscription_id': self.id},
        }

    def action_open_renew_wizard(self):
        """Open the renewal wizard."""
        self.ensure_one()
        return {
            'name': _('Renew Subscription'),
            'type': 'ir.actions.act_window',
            'res_model': 'solt.subscription.renew.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_subscription_id': self.id},
        }

    def action_view_invoices(self):
        """Open the related invoices using the action matching the subscription type."""
        self.ensure_one()
        if self.type == 'purchase':
            action = self.env['ir.actions.actions']._for_xml_id('account.action_move_in_invoice_type')
        else:
            action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        if self.invoice_count > 1:
            action['domain'] = [('id', 'in', self.invoice_ids.ids)]
        elif self.invoice_count == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = self.invoice_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    # === LIFECYCLE HOOKS === #

    def _post_activate(self):
        """Hook called after a subscription transitions to 'active' state.
        Override in integration modules to trigger deployment actions.
        """

    def _post_close(self):
        """Hook called after a subscription transitions to 'closed' state.
        Override in integration modules to trigger teardown actions.
        """

    def _post_archived(self):
        """Hook called after a subscription is archived (active=False).
        Override in integration modules to trigger final cleanup actions.
        """

    def _post_plan_change(self, old_plan, new_plan):
        """Hook called after an in-place plan change.
        Override in integration modules to update configuration without redeploying.

        :param old_plan: solt.recurring.plan - the previous plan
        :param new_plan: solt.recurring.plan - the new plan
        """

    def _post_upsell(self, new_lines):
        """Hook called after upsell lines are added to the subscription.
        Override in integration modules to deploy new resources.

        :param new_lines: solt.subscription.line recordset - the newly added lines
        """

    # === PRORATION HELPERS === #

    @staticmethod
    def _compute_period_days(plan):
        """Compute the approximate billing period in days for proration calculations.

        :param plan: solt.recurring.plan record
        :return: int number of days in the billing period
        """
        billing_unit = plan.billing_period_unit
        billing_value = plan.billing_period_value
        if billing_unit == 'day':
            return billing_value
        elif billing_unit == 'week':
            return billing_value * 7
        elif billing_unit == 'month':
            return billing_value * 30
        elif billing_unit == 'year':
            return billing_value * 365
        return billing_value

    def _compute_proration_factor(self, plan=None):
        """Compute the proration factor (fraction of the current period remaining).

        :param plan: solt.recurring.plan (defaults to self.plan_id)
        :return: float between 0.0 and 1.0
        """
        self.ensure_one()
        if plan is None:
            plan = self.plan_id
        today = fields.Date.today()
        next_invoice = self.next_invoice_date or today
        days_remaining = (next_invoice - today).days
        if days_remaining <= 0:
            return 0.0
        period_days = self._compute_period_days(plan)
        if period_days <= 0:
            return 0.0
        return days_remaining / period_days

    def _create_proration_move(self, proration_line_data, move_type='out_invoice'):
        """Create a proration invoice or credit note from a list of line data dicts.

        :param proration_line_data: list of dicts with keys product_id, description, quantity,
               price_unit, and optionally tax_ids
        :param move_type: 'out_invoice' for upgrade, 'out_refund' for downgrade
        :return: account.move record (posted) or empty recordset if no lines
        """
        self.ensure_one()
        if not proration_line_data:
            return self.env['account.move']

        today = fields.Date.today()
        invoice_vals = self._prepare_invoice()
        invoice_vals.update({
            'invoice_date': today,
            'move_type': move_type,
            'invoice_line_ids': [],
        })

        for line_data in proration_line_data:
            product = self.env['product.product'].browse(line_data['product_id'])
            accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=self.fiscal_position_id)
            income_account = accounts.get('income')

            line_vals = {
                'product_id': line_data['product_id'],
                'name': line_data['description'],
                'quantity': line_data['quantity'],
                'price_unit': abs(line_data['price_unit']),
                'subscription_id': self.id,
            }
            if income_account:
                line_vals['account_id'] = income_account.id
            if line_data.get('tax_ids'):
                line_vals['tax_ids'] = [Command.set(line_data['tax_ids'])]

            invoice_vals['invoice_line_ids'].append(Command.create(line_vals))

        if not invoice_vals['invoice_line_ids']:
            return self.env['account.move']

        proration_move = self.env['account.move'].sudo().create(invoice_vals)
        proration_move.action_post()
        return proration_move

    def _create_unused_period_credit_note(self):
        """Generate a credit note for the unused portion of the current billing period.

        :return: account.move (posted credit note) or empty recordset
        """
        self.ensure_one()
        proration_factor = self._compute_proration_factor()
        if proration_factor <= 0:
            return self.env['account.move']

        credit_line_data = []
        for line in self.subscription_line_ids:
            prorated_amount = line.price_unit * proration_factor
            if prorated_amount > 0:
                credit_line_data.append({
                    'product_id': line.product_id.id,
                    'description': _('%s - Unused period credit', line.product_id.name),
                    'quantity': line.product_uom_qty,
                    'price_unit': prorated_amount,
                    'tax_ids': line.tax_ids.ids,
                })

        return self._create_proration_move(credit_line_data, move_type='out_refund')

    # === PLAN CHANGE IN-PLACE === #

    def _change_plan_inplace(self, new_plan):
        """Change the subscription plan in-place without creating a new subscription.

        Updates plan_id, recalculates line prices, generates a proration invoice or credit
        note for the prorated difference, adjusts next_invoice_date, and calls _post_plan_change.

        :param new_plan: solt.recurring.plan record to switch to
        :return: account.move (proration document) or empty recordset
        """
        self.ensure_one()
        old_plan = self.plan_id
        today = fields.Date.today()

        old_line_prices = {line.id: line.price_subtotal for line in self.subscription_line_ids}
        old_proration_factor = self._compute_proration_factor(old_plan)

        self.plan_id = new_plan
        for line in self.subscription_line_ids:
            line._recalculate_price_for_plan(new_plan, old_plan)

        new_proration_factor = self._compute_proration_factor(new_plan)

        proration_line_data = []
        total_difference = 0.0
        for line in self.subscription_line_ids:
            old_prorated = old_line_prices.get(line.id, 0.0) * old_proration_factor
            new_prorated = line.price_subtotal * new_proration_factor
            difference = new_prorated - old_prorated
            if difference != 0:
                total_difference += difference
                proration_line_data.append({
                    'product_id': line.product_id.id,
                    'description': _('%s - Plan change adjustment (%s → %s)', line.product_id.name, old_plan.name, new_plan.name),
                    'quantity': line.product_uom_qty,
                    'price_unit': difference / line.product_uom_qty if line.product_uom_qty else difference,
                    'tax_ids': line.tax_ids.ids,
                })

        proration_move = self.env['account.move']
        if total_difference > 0:
            proration_move = self._create_proration_move(proration_line_data, move_type='out_invoice')
            self.message_post(body=_("Plan upgraded from %s to %s. Proration invoice: %s", old_plan.name, new_plan.name, proration_move._get_html_link()))
        elif total_difference < 0:
            proration_move = self._create_proration_move(proration_line_data, move_type='out_refund')
            self.message_post(body=_("Plan downgraded from %s to %s. Credit note: %s", old_plan.name, new_plan.name, proration_move._get_html_link()))
        else:
            self.message_post(body=_("Plan changed from %s to %s (same price, no proration).", old_plan.name, new_plan.name))

        self.next_invoice_date = today + new_plan.billing_period
        self._post_plan_change(old_plan, new_plan)
        return proration_move

    # === UPSELL === #

    def _upsell_add_lines(self, wizard_lines):
        """Add new product lines to this active subscription with proration.

        Creates subscription lines from the wizard lines, generates a prorated
        invoice for the remaining period, and calls _post_upsell hook.

        :param wizard_lines: solt.subscription.renew.wizard.line recordset
        :return: account.move (proration invoice) or empty recordset
        """
        self.ensure_one()
        if self.state != 'active':
            raise UserError(_("Upsell is only available for active subscriptions."))

        proration_factor = self._compute_proration_factor()
        new_lines = self.env['solt.subscription.line']
        proration_line_data = []

        for wizard_line in wizard_lines:
            if wizard_line.price_unit:
                resolved_price = wizard_line.price_unit
            else:
                resolved_price = self.env['solt.subscription.line']._get_price_from_pricing(
                    wizard_line.product_id, self.plan_id, self.pricelist_id,
                    self.currency_id, self.company_id,
                )
            product_taxes = wizard_line.product_id.taxes_id.filtered(lambda tax: tax.company_id == self.company_id)
            subscription_line = self.env['solt.subscription.line'].create({
                'subscription_id': self.id,
                'product_id': wizard_line.product_id.id,
                'name': wizard_line.name or wizard_line.product_id.get_product_multiline_description_sale(),
                'product_uom_qty': wizard_line.product_uom_qty,
                'price_unit': resolved_price,
                'product_uom_id': wizard_line.product_id.uom_id.id,
                'tax_ids': [Command.set(product_taxes.ids)],
            })
            new_lines |= subscription_line

            if proration_factor > 0:
                proration_line_data.append({
                    'product_id': wizard_line.product_id.id,
                    'description': _('%s - Prorated for remaining period', wizard_line.product_id.name),
                    'quantity': wizard_line.product_uom_qty,
                    'price_unit': resolved_price * proration_factor,
                    'tax_ids': product_taxes.ids,
                })

        proration_move = self.env['account.move']
        if proration_line_data:
            proration_move = self._create_proration_move(proration_line_data)
            self.message_post(body=_("Upsell: %d product(s) added. Proration invoice: %s", len(new_lines), proration_move._get_html_link()))
        else:
            self.message_post(body=_("Upsell: %d product(s) added (no proration, billing starts next period).", len(new_lines)))

        self._post_upsell(new_lines)
        return proration_move

    # === SERVICE CHANGE === #

    def _prepare_service_change_data(self, new_subscription):
        """Prepare data for a service change, classifying products kept, added, and removed.

        :param new_subscription: solt.subscription - the new subscription being created
        :return: dict with old_subscription, new_subscription, keep_products, create_products, destroy_products
        """
        old_products = self.subscription_line_ids.mapped('product_id')
        new_products = new_subscription.subscription_line_ids.mapped('product_id')
        return {
            'old_subscription': self,
            'new_subscription': new_subscription,
            'keep_products': old_products & new_products,
            'create_products': new_products - old_products,
            'destroy_products': old_products - new_products,
        }

    def _execute_service_change(self, service_change_data):
        """Execute the service change resource transfer.

        Override in integration modules to handle resource management based on
        keep_products, create_products, and destroy_products classifications.

        :param service_change_data: dict returned by _prepare_service_change_data
        """

    # === INVOICING METHODS === #
    def _update_next_invoice_date(self):
        """Update the next invoice date based on the billing period."""
        for subscription in self:
            if subscription.next_invoice_date and subscription.plan_id.billing_period:
                subscription.next_invoice_date = subscription.next_invoice_date + subscription.plan_id.billing_period

    def _recurring_invoice_domain(self, extra_domain=None):
        if not extra_domain:
            extra_domain = []
        current_date = fields.Date.today()
        search_domain = [
            ('is_batch', '=', False),
            ('is_invoice_cron', '=', False),
            ('state', '=', 'progress'),
            ('payment_exception', '=', False),
            ('pending_transaction', '=', False),
            ('company_id.active', '=', True),
            '|',
            ('next_invoice_date', '<=', current_date),
            ('end_date', '<=', current_date),
        ]
        if extra_domain:
            search_domain = expression.AND([search_domain, extra_domain])
        return search_domain

    def _recurring_invoice_get_subscriptions(self, batch_size=30):
        """Return a boolean and an iterable of recordsets.
        The boolean is true if batch_size is smaller than the number of remaining records
        """
        need_cron_trigger = False
        limit = False
        if self:
            domain = [('id', 'in', self.ids), ('state', 'in', SUBSCRIPTION_ACTIVE_STATE), ('company_id.active', '=', True)]
            batch_size = False
        else:
            domain = self._recurring_invoice_domain()
            limit = batch_size and batch_size + 1

        all_subscriptions = self.read_group(domain, ['id:array_agg'], ['company_id', 'currency_id', 'partner_id', 'payment_token_id'], limit=limit, lazy=False)
        all_subscriptions = [self.browse(res['id']) for res in all_subscriptions]

        if batch_size:
            need_cron_trigger = len(all_subscriptions) > batch_size
            all_subscriptions = all_subscriptions[:batch_size]

        return all_subscriptions, need_cron_trigger

    def _subscription_auto_close(self):
        """Handle contracts that need to be automatically closed/set to renews.
        This method is only called during a cron
        """
        current_date = fields.Date.context_today(self)
        close_contract_ids = self.filtered(lambda contract: contract.end_date and contract.end_date <= current_date)
        close_contract_ids.set_close()
        return close_contract_ids

    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()

        values = {
            'ref': '',
            'invoice_date': self.next_invoice_date,
            'move_type': 'out_invoice' if self.type == 'sale' else 'in_invoice',
            'narration': self.internal_note,
            'currency_id': self.currency_id.id,
            # 'team_id': self.team_id.id,
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.commercial_partner_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(self.partner_id)).id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_user_id': self.user_id.id,
            'company_id': self.company_id.id,
            'invoice_line_ids': [],
            'user_id': self.user_id.id,
        }
        if self.journal_id:
            values['journal_id'] = self.journal_id.id
        return values

    def _create_account_invoices(self, invoice_vals_list, final):
        """Small method to allow overriding the behavior right after an invoice is created."""
        # Manage the creation of invoices in sudo because a salesperson must be able to generate an invoice from a
        # sale order without "billing" access rights. However, he should not be able to create an invoice from scratch.
        return self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals_list)

    def _create_invoices(self, final=False):
        """Create invoice(s) for the given Sales Order(s).

        :param bool final: if True, refunds will be generated if necessary
        :returns: created invoices
        :rtype: `account.move` recordset
        :raises: UserError if one of the orders has no invoiceable lines.
        """
        if not self.env['account.move'].has_access('create'):
            try:
                self.check_access('write')
            except AccessError:
                return self.env['account.move']

        invoice_vals_list = []
        for sub in self:
            if sub.partner_id.lang:
                sub = sub.with_context(lang=sub.partner_id.lang)
            sub = sub.with_company(sub.company_id)
            invoice_vals = sub._prepare_invoice()
            invoice_line_vals = []
            for line in sub.subscription_line_ids:
                invoice_line_vals.append(Command.create(line._prepare_invoice_line()))
            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list and self.env.context.get('raise_if_nothing_to_invoice', True):
            raise UserError(_("You are trying to invoice recurring orders that are past their end date. Please change their end date or renew them before creating new invoices."))

        if len(invoice_vals_list) < len(self):
            for invoice in invoice_vals_list:
                sequence = 1
                for line in invoice['invoice_line_ids']:
                    line[2]['sequence'] = sequence or line[2]['sequence']
                    sequence += 1

        moves = self._create_account_invoices(invoice_vals_list, final)

        if final and (moves_to_switch := moves.sudo().filtered(lambda m: m.amount_total < 0)):
            with self.env.protecting([moves._fields['team_id']], moves_to_switch):
                moves_to_switch.action_switch_move_type()
                self.invoice_ids._set_reversed_entry(moves_to_switch)

        return moves

    def _get_traceback_body(self, exc, body):
        if not str2bool(self.env['ir.config_parameter'].sudo().get_param('solt_recurring_payment.full_mail_traceback')):
            return plaintext2html("%s\n\n%s" % (body, str(exc)))
        return plaintext2html("%s\n\n%s\n%s" % (body, ''.join(traceback.format_tb(exc.__traceback__)), str(exc)))

    def _get_subscription_mail_payment_context(self, mail_ctx=None):
        self.ensure_one()
        if not mail_ctx:
            mail_ctx = {}
        return {**self.env.context, **mail_ctx, **{'total_amount': self.recurring_total, 'currency_name': self.currency_id.name, 'responsible_email': self.user_id.email, 'code': self.name}}

    def _process_auto_invoice(self, invoice):
        """Hook for extension, to support different invoice states"""
        invoice.action_post()
        return

    def _handle_subscription_payment_failure(self, invoice, transaction):
        current_date = fields.Date.today()
        reminder_mail_template = self.env.ref('solt_recurring_payment.email_payment_reminder', raise_if_not_found=False)
        close_mail_template = self.env.ref('solt_recurring_payment.email_payment_close', raise_if_not_found=False)
        invoice.unlink()
        for order in self:
            auto_close_days = order.plan_id.auto_close_limit or 15
            date_close = order.next_invoice_date + relativedelta(days=auto_close_days)
            close_contract = current_date >= date_close
            email_context = order._get_subscription_mail_payment_context()
            _logger.info('Failed to create recurring invoice for contract %s', order.name)
            if close_contract:
                close_mail_template.with_context(**email_context).send_mail(order.id)
                _logger.debug("Sending Contract Closure Mail to %s for contract %s and closing contract", order.partner_id.email, order.id)
                msg_body = _("Automatic payment failed after multiple attempts. Contract closed automatically.")
                order.message_post(body=msg_body)
                subscription_values = {'payment_exception': False}
                # close the contract as needed
                order.set_close(close_reason_id=order.env.ref('solt_recurring_payment.close_reason_auto_close_limit').id)
            else:
                msg_body = _('Automatic payment failed. No email sent this time. Error: %s', transaction and transaction.state_message or _('No valid Payment Method'))
                if (fields.Date.today() - order.next_invoice_date).days in [2, 7, 14]:
                    email_context.update({'date_close': date_close, 'payment_token': order.payment_token_id.display_name})
                    reminder_mail_template.with_context(**email_context).send_mail(order.id)
                    _logger.debug("Sending Payment Failure Mail to %s for contract %s and setting contract to pending", order.partner_id.email, order.id)
                    msg_body = _('Automatic payment failed. Email sent to customer. Error: %s', transaction and transaction.state_message or _('No Payment Method'))
                order.message_post(body=msg_body)
                # payment failed (not catched in exception) but we should not retry directly.
                # flag with is_batch to avoid processing it again in another batch
                subscription_values = {'payment_exception': False, 'is_batch': True}
            order.write(subscription_values)

    def _handle_automatic_invoices(self, invoice, auto_commit):
        """This method handle the subscription with or without payment token"""
        Mail = self.env['mail.mail']
        # Set the contract in exception. If something go wrong, the exception remains.
        self.with_context(mail_notrack=True).write({'payment_exception': True})
        payment_token = self.payment_token_id

        if not payment_token or len(payment_token) > 1:
            self._process_auto_invoice(invoice)
            return invoice

        if not payment_token.partner_id.country_id:
            msg_body = _('Automatic payment failed. No country specified on payment_token\'s partner')
            for order in self:
                order.message_post(body=msg_body)
            invoice.unlink()
            self._subscription_commit_cursor(auto_commit)
            return

        try:
            # execute payment
            self.pending_transaction = True
            if invoice.currency_id.compare_amounts(invoice.amount_total_signed, 0) < 0:
                # Something is wrong, we are trying to create a negative transaction. probably because a manual change in the order
                # payment_exception is still true. We keep the draft invoice to allow salesmen understand what is going on.
                self.pending_transaction = False
                msg_body = _("Automatic payment failed. Check the corresponding invoice %s. We can't automatically process negative payment", invoice._get_html_link())
                for order in self:
                    order.message_post(body=msg_body)
                self._subscription_commit_cursor(auto_commit)
                # We return the draft invoice because it should be analyzed by the accounting to understand the issue
                return invoice
            transaction = self._do_payment(payment_token, invoice, auto_commit=auto_commit)
            # commit change as soon as we try the payment, so we have a trace in the payment_transaction table

            # if no transaction or failure, log error, rollback and remove invoice
            if not transaction or transaction.renewal_state == 'cancel':
                self._handle_subscription_payment_failure(invoice, transaction)
                self._subscription_commit_cursor(auto_commit)
                return
            # if transaction is a success, post a message
            elif transaction.renewal_state == 'authorized':
                self._subscription_commit_cursor(auto_commit)
                invoice._post()
                self._subscription_commit_cursor(auto_commit)

        except Exception as e:
            payment_state = _("Payment not recorded")
            error_message = _("Error during renewal of contract %s %s %s", self.ids, ', '.join(self.mapped('name')), payment_state)
            body = self._get_traceback_body(e, error_message)
            _logger.exception(error_message)
            self._subscription_rollback_cursor(auto_commit)
            mail = Mail.sudo().create(
                [{'body_html': body, 'subject': error_message, 'email_to': order._get_subscription_mail_payment_context().get('responsible_email'), 'auto_delete': True} for order in self]
            )
            mail.send()
            if invoice.state == 'draft':
                invoice.unlink()
                return
        return invoice

    def _activate_plan_change_after_payment(self):
        """Activate new subscription and close old one after plan change invoice is paid.
        Called when plan change upgrade invoice is paid."""
        # Find subscriptions that have pending plan changes
        for subscription in self.filtered(lambda s: s.pending_transaction):
            # Find related new subscription (has this subscription as origin)
            new_subscription = self.env['solt.subscription'].search([
                ('origin_subscription_id', '=', subscription.id),
                ('state', '=', 'draft'),
                ('plan_id', '!=', subscription.plan_id.id)
            ], limit=1)

            if new_subscription:
                # Use sudo to bypass permission checks
                subscription_sudo = subscription.sudo()
                new_subscription_sudo = new_subscription.sudo()

                # Activate new subscription
                new_subscription_sudo.action_confirm()

                # Close old subscription (state closed)
                subscription_sudo.set_close(
                    close_reason_id=self.env.ref(
                        'solt_recurring_payment.close_reason_plan_change',
                        raise_if_not_found=False
                    ).id or False
                )

                # Clear pending flag
                subscription_sudo.pending_transaction = False

                subscription_sudo.message_post(
                    body=_("Plan change payment successful. New subscription activated: %s",
                        new_subscription_sudo._get_html_link())
                )
                new_subscription_sudo.message_post(
                    body=_("Plan change completed. Previous subscription closed: %s",
                        subscription_sudo._get_html_link())
                )

    def _subscription_launch_cron_parallel(self, batch_size):
        self.env.ref('solt_recurring_payment.ir_cron_recurring_payment_invoice')._trigger()

    def validate_and_send_invoice(self, invoice):
        """
        Send the invoice using the plan-specific template if available.

        This method prepares the email context and sends the invoice PDF to the customer
        using the template defined on the subscription plan, if present.

        :param invoice: The invoice record to send.
        """
        email_context = {
            **self.env.context.copy(),
            'total_amount': invoice.amount_total,
            'email_to': invoice.partner_id.email,
            'code': ', '.join(subscription.name for subscription in self),
            'currency': invoice.currency_id.name,
            'no_new_invoice': True,
        }
        auto_commit = not bool(config['test_enable'] or config['test_file'])
        self._subscription_commit_cursor(auto_commit)
        if self.plan_id.invoice_mail_template_id:
            _logger.debug("Sending Invoice Mail to %s for subscription %s", self.partner_id.mapped('email'), self.ids)
            invoice.with_context(**email_context)._generate_pdf_and_send_invoice(self.plan_id.invoice_mail_template_id)

    @api.model
    def _process_invoices_to_send(self, account_moves):
        for invoice in account_moves:
            if not invoice.is_move_sent and invoice._is_ready_to_be_sent() and invoice.state == 'posted':
                subscription = invoice.line_ids.subscription_id
                subscription.validate_and_send_invoice(invoice)
                invoice.message_subscribe(subscription.user_id.partner_id.ids)
            elif invoice.line_ids.subscription_id:
                invoice.message_subscribe(invoice.line_ids.subscription_id.user_id.partner_id.ids)

    def _create_recurring_invoice(self, batch_size=30):
        auto_commit = not bool(config['test_enable'] or config['test_file'])
        all_subscriptions, need_cron_trigger = self._recurring_invoice_get_subscriptions(batch_size=batch_size)
        if not all_subscriptions:
            return self.env['account.move']

        # We mark current batch as having been seen by the cron
        for subscriptions in all_subscriptions:
            subscriptions.is_invoice_cron = True
            # Don't spam sale with assigned emails.
            subscriptions = subscriptions.with_context(mail_auto_subscribe_no_notify=True)
            # Close ending subscriptions
            auto_close_subscription = subscriptions.filtered_domain([('end_date', '!=', False)])
            closed_contract = auto_close_subscription._subscription_auto_close()
            subscriptions -= closed_contract

        account_moves = self.env['account.move']
        move_to_send_ids = []
        for subscriptions in all_subscriptions:
            if len(subscriptions) == 1:
                subscriptions = subscriptions[0]  # Trick to not prefetch other subscriptions is all_subscription is recordset, as the cache is currently invalidated at each iteration

            # We check that the subscriptions should not be processed or that it has not already been set to "in exception" by previous crons
            # We only invoice contract in sale state. Locked contracts are invoiced in advance. They are frozen.
            subscriptions = subscriptions.filtered(lambda s: s.state == 'active' and not s.payment_exception)
            if not subscriptions:
                continue
            for subscription in subscriptions:
                try:
                    self._subscription_commit_cursor(auto_commit)  # To avoid a rollback in case something is wrong, we create the invoices one by one
                    draft_invoices = subscription.invoice_ids.filtered(lambda am: am.state == 'draft')
                    if subscription.payment_token_id and draft_invoices:
                        draft_invoices.button_cancel()
                    elif draft_invoices:
                        # Skip subscription if no payment_token, and it has a draft invoice
                        continue
                    try:
                        with self.env.protecting([subscription._fields['recurring_total']], subscription):
                            invoice = subscription.with_context(recurring_automatic=True)._create_invoices(final=True)
                    except Exception as e:
                        # We only raise the error in test, if the transaction is broken we should raise the exception
                        if not auto_commit and isinstance(e, TransactionRollbackError):
                            raise
                        # we suppose that the payment is run only once a day
                        self._subscription_rollback_cursor(auto_commit)
                        email_context = subscription._get_subscription_mail_payment_context()
                        error_message = _("Error during renewal of contract %s (Payment not recorded)", subscription.name)
                        _logger.exception(error_message)
                        body = self._get_traceback_body(e, error_message)
                        mail = self.env['mail.mail'].sudo().create({'body_html': body, 'subject': error_message, 'email_to': email_context['responsible_email'], 'auto_delete': True})
                        mail.send()
                        continue
                    self._subscription_commit_cursor(auto_commit)
                    # Handle automatic payment or invoice posting
                    with self.env.protecting([subscription._fields['recurring_total']], subscription):
                        existing_invoices = subscription.with_context(recurring_automatic=True)._handle_automatic_invoices(invoice, auto_commit) or self.env['account.move']
                    account_moves |= existing_invoices
                    if all(inv.state != 'draft' for inv in existing_invoices):
                        # when the invoice is not confirmed, we keep it and keep the payment_exception flag
                        # Failed payment that delete the invoice will also be handled here and the flag will be removed
                        subscription.with_context(mail_notrack=True).payment_exception = False
                    if not subscription.payment_token_id:  # _get_auto_invoice_grouping_keys groups by token too
                        move_to_send_ids += existing_invoices.ids
                    self._subscription_commit_cursor(auto_commit)
                except Exception:
                    name_list = subscription.mapped('name')
                    _logger.exception("Error during renewal of contract %s", "; ".join(name_list))
                    self._subscription_rollback_cursor(auto_commit)
        self._subscription_commit_cursor(auto_commit)
        self._process_invoices_to_send(self.env['account.move'].browse(move_to_send_ids))
        self._subscription_commit_cursor(auto_commit)
        # There is still some subscription to process. Then, make sure the CRON will be triggered again asap.
        if need_cron_trigger:
            self._subscription_launch_cron_parallel(batch_size)
        else:
            failing_subscriptions = self.search(['|', ('is_batch', '=', True), ('is_invoice_cron', '=', True)])
            failing_subscriptions.write({'is_batch': False, 'is_invoice_cron': False})
            self._subscription_commit_cursor(auto_commit)
        return account_moves

    def _do_payment(self, payment_token, invoice, auto_commit=False):
        values = [
            {
                'provider_id': payment_token.provider_id.id,
                'payment_method_id': payment_token.payment_method_id.id,
                'subscription_ids': self.ids,
                'amount': invoice.amount_total,
                'currency_id': invoice.currency_id.id,
                'partner_id': invoice.partner_id.id,
                'token_id': payment_token.id,
                'operation': 'offline',
                'invoice_ids': [(6, 0, [invoice.id])],
                'subscription_action': 'automatic_send_mail',
            }
        ]
        transactions_sudo = self.env['payment.transaction'].sudo().create(values)
        self._subscription_commit_cursor(auto_commit)
        for tx_sudo in transactions_sudo:
            self.env.cr.execute("SELECT 1 FROM payment_transaction WHERE id=%s FOR UPDATE", [tx_sudo.id])
            tx_sudo._send_payment_request()
        return transactions_sudo

    def _subscription_commit_cursor(self, auto_commit):
        if auto_commit:
            self.env.cr.commit()
        else:
            self.env.flush_all()

    def _subscription_rollback_cursor(self, auto_commit):
        if auto_commit:
            self.env.cr.rollback()

    # === HELPER METHODS === #

    def _get_portal_return_action(self):
        """Return the action for portal redirection."""
        return self.env.ref('solt_recurring_payment.solt_subscription_action')

    def get_portal_url(self, suffix=None, report_type=None, download=None, query_string=None, anchor=None):
        """Get the portal URL for this subscription."""
        self.ensure_one()
        url = f'/my/subscriptions/{self.id}'
        if suffix:
            url += suffix
        if query_string:
            url += '?' + query_string
        return url

    @api.model
    def _cron_invoice_subscriptions(self):
        return self._create_recurring_invoice()

    def _get_unpaid_subscriptions(self):
        # TODO FLDA SEE THAT O_O
        # We don't use CURRENT_DATE to allow using freeze_time in tests.
        today = fields.Datetime.today()
        self.env.cr.execute(
            """
            WITH payment_limit_query AS (SELECT (aml2.dm + INTERVAL '1 day' * COALESCE(ssp.auto_close_limit, 15)) AS "payment_limit",
                                                aml2.dm                                                           AS date_maturity,
                                                ssp.billing_period_unit                                           AS unit,
                                                ssp.billing_period_value                                          AS duration,
                                                CASE
                                                    WHEN ssp.billing_period_unit = 'week' THEN INTERVAL '1 day' * 7 * ssp.billing_period_value
                                                    WHEN ssp.billing_period_unit = 'month' THEN INTERVAL '1 day' * 30 * ssp.billing_period_value
                                                    WHEN ssp.billing_period_unit = 'year' THEN INTERVAL '1 day' * 365 * ssp.billing_period_value
                                                    END                                                           AS conversion,
                                                ssp.billing_period_value || ' ' || ssp.billing_period_unit        AS recurrence,
                                                am.payment_state                                                  AS payment_state,
                                                am.id                                                             AS am_id,
                                                sub.id                                                            AS so_id,
                                                sub.next_invoice_date
                                         FROM solt_subscription sub
                                                  JOIN account_move_line aml ON aml.subscription_id = sub.id
                                                  JOIN account_move am ON am.id = aml.move_id
                                                  JOIN solt_recurring_plan ssp ON ssp.id = sub.plan_id
                                                  LEFT JOIN LATERAL ( SELECT MAX(date_maturity) AS dm FROM account_move_line aml WHERE aml.move_id = am.id) AS aml2 ON TRUE
                                         WHERE sub.state = 'progress'
                                           AND am.payment_state = 'not_paid'
                                           AND am.move_type = 'out_invoice'
                                           AND am.state = 'posted'
                                         GROUP BY so_id, am_id, ssp.auto_close_limit, payment_state, aml2.dm, ssp.billing_period_unit, ssp.billing_period_value, sub.next_invoice_date)
            SELECT payment_limit::DATE,
                   date_maturity,
                   recurrence,
                   next_invoice_date - plq.conversion AS last_invoice_date,
                   payment_state,
                   am_id,
                   so_id,
                   next_invoice_date
            FROM payment_limit_query plq
            WHERE payment_limit < %s
              and payment_limit >= (next_invoice_date - plq.conversion)::DATE
            """,
            [today.strftime('%Y-%m-%d')],
        )
        return self.env.cr.dictfetchall()

    def _handle_unpaid_subscriptions(self):
        unpaid_result = self._get_unpaid_subscriptions()
        return {res['so_id']: res['am_id'] for res in unpaid_result}

    def _get_expired_subscriptions(self):
        # We don't use CURRENT_DATE to allow using freeze_time in tests.
        today = fields.Datetime.today()
        self.env.cr.execute(
            """
            SELECT (sub.next_invoice_date + INTERVAL '1 day' * COALESCE(ssp.auto_close_limit, 15)) AS "payment_limit",
                   sub.next_invoice_date,
                   sub.id                                                                          AS so_id
            FROM solt_subscription sub
                     LEFT JOIN solt_recurring_plan ssp ON ssp.id = sub.plan_id
            WHERE state = 'progress'
              AND (sub.next_invoice_date + INTERVAL '1 day' * COALESCE(ssp.auto_close_limit, 15)) < %s
            """,
            [today.strftime('%Y-%m-%d')],
        )
        return self.env.cr.dictfetchall()

    def _cron_check_expiration(self):
        # Flush models according to following SQL requests
        self.env['solt.subscription'].flush_model(fnames=['subscription_line_ids', 'plan_id', 'state', 'state', 'next_invoice_date'])
        self.env['account.move'].flush_model(fnames=['payment_state', 'line_ids'])
        self.env['account.move.line'].flush_model(fnames=['move_id', 'sale_line_ids'])
        self.env['solt.recurring.plan'].flush_model(fnames=['auto_close_limit'])
        today = fields.Date.today()
        # set to close if date is passed or if renewed sale order passed
        domain_close = [('end_date', '<', today), ('state', 'in', SUBSCRIPTION_ACTIVE_STATE)]
        subscriptions_close = self.search(domain_close)
        unpaid_results = self._handle_unpaid_subscriptions()
        unpaid_ids = unpaid_results.keys()
        expired_result = self._get_expired_subscriptions()
        expired_ids = [r['so_id'] for r in expired_result]
        subscriptions_close |= self.env['solt.subscription'].browse(unpaid_ids) | self.env['solt.subscription'].browse(expired_ids)
        auto_commit = not bool(config['test_enable'] or config['test_file'])
        expired_close_reason = self.env.ref('solt_recurring_payment.close_reason_auto_close_limit')
        unpaid_close_reason = self.env.ref('solt_recurring_payment.close_reason_unpaid')
        for batched_to_close in split_every(30, subscriptions_close.ids, self.env['solt.subscription'].browse):
            unpaid_so = self.env['solt.subscription']
            expired_so = self.env['solt.subscription']
            for so in batched_to_close:
                if so.id in unpaid_ids:
                    unpaid_so |= so
                    account_move = self.env['account.move'].browse(unpaid_results[so.id])
                    so.message_post(body=_("The last invoice (%s) of this subscription is unpaid after the due date.", account_move._get_html_link()), partner_ids=so.team_user_id.partner_id.ids)
                elif so.id in expired_ids:
                    expired_so |= so

            unpaid_so.set_close(close_reason_id=unpaid_close_reason.id)
            expired_so.set_close(close_reason_id=expired_close_reason.id)
            (batched_to_close - unpaid_so - expired_so).set_close()
            if auto_commit:
                self.env.cr.commit()
        return {'closed': subscriptions_close.ids}

    @api.model
    def _cron_auto_archive_subscriptions(self):
        """Archive closed subscriptions after the configured delay has passed.

        For each closed subscription, checks whether the number of days since
        close_date exceeds the plan's auto_archive_delay. If so, archives the
        subscription (active=False) and calls the _post_archived hook.
        """
        today = fields.Date.today()
        closed_subscriptions = self.search([
            ('state', '=', 'closed'),
            ('active', '=', True),
            ('close_date', '!=', False),
        ])
        subscriptions_to_archive = self.env['solt.subscription']
        for subscription in closed_subscriptions:
            archive_delay_days = subscription.plan_id.auto_archive_delay or 15
            archive_deadline = subscription.close_date + relativedelta(days=archive_delay_days)
            if today >= archive_deadline:
                subscriptions_to_archive |= subscription

        if subscriptions_to_archive:
            subscriptions_to_archive.write({'active': False})
            _logger.info(
                "Auto-archived %d closed subscriptions: %s",
                len(subscriptions_to_archive),
                ', '.join(subscriptions_to_archive.mapped('name')),
            )
        return subscriptions_to_archive

    def _assign_token(self, tx):
        """Callback method to assign a token after the validation of a transaction.
        Note: self.ensure_one()
        :param recordset tx: The validated transaction, as a `payment.transaction` record
        :return: Whether the conditions were met to execute the callback
        """
        if tx.renewal_state == 'authorized':
            self.payment_token_id = tx.token_id.id
            return True
        return False

    def set_open(self):
        """Reopen closed subscriptions and set them to active state.

        This method reopens subscriptions that were previously closed, removing the
        end date and close reason. If a subscription had an end date, it schedules
        a follow-up activity for the responsible user to review the reopened subscription.
        """
        for order in self:
            if order.state == 'closed' and order.end_date:
                order.end_date = False
                reopen_activity_body = _("Subscription %s has been reopened. The end date has been removed", order._get_html_link())
                order.activity_schedule('mail.mail_activity_data_todo', summary=_("Check reopened subscription"), note=reopen_activity_body, user_id=order.user_id.id)
        self.update({'state': 'active', 'close_reason_id': False})

    def _send_success_mail(self, invoices, tx):
        """
        Send mail once the transaction to pay subscription invoice has succeeded
        :param invoices: one or more account.move recordset
        :param tx: single payment.transaction
        """
        template = self.env.ref('solt_recurring_payment.email_payment_success').sudo()
        current_date = fields.Date.today()
        subscription_ids = []
        invoice_values = {}
        for invoice in invoices:
            # We may have different subscriptions per invoice
            subscriptions = invoice.invoice_line_ids.subscription_id
            if not subscriptions or invoice.is_move_sent or not invoice._is_ready_to_be_sent() or invoice.state != 'posted':
                continue
            invoice_values = {sub.id: invoice for sub in subscriptions}
            subscription_ids += subscriptions.ids
        for subscription in self.browse(subscription_ids):
            linked_invoices = invoice_values[subscription.id]
            # Most of the time, we invoice one sub per invoice
            next_date = subscription.next_invoice_date or current_date
            # if no recurring next date, have next invoice be today + interval
            if not subscription.next_invoice_date:
                error_msg = "The success mail could not be sent for subscription %s and invoice %s." % (subscription.name, invoice.name)
                _logger.error(error_msg)
                continue
            email_context = {
                **self.env.context.copy(),
                'payment_token': subscription.payment_token_id.payment_details,
                'renewed': True,
                'total_amount': tx.amount,
                'next_date': next_date,
                'previous_date': subscription.next_invoice_date,
                'email_to': subscription.partner_id.email,
                'subscription_name': subscription.name,
                'currency': subscription.currency_id.name,
                'date_end': subscription.end_date,
            }
            _logger.debug("Sending Payment Confirmation Mail to %s for subscription %s", subscription.partner_id.email, subscription.id)

            linked_invoices.is_move_sent = True
            linked_invoices.with_context(**email_context)._generate_pdf_and_send_invoice(template)

    def _subscription_post_success_payment(self, transaction, invoices, automatic=True):
        """
         Action done after the successful payment has been performed
        :param transaction: single payment.transaction record
        :param invoices: account.move recordset
        :param automatic: True if the transaction was created during the subscription invoicing cron
        """
        self.ensure_one()
        transaction.ensure_one()
        for invoice in invoices:
            invoice.write({'payment_reference': transaction.reference, 'ref': transaction.reference})
            if automatic:
                msg_body = _(
                    'Automatic payment succeeded. Payment reference: %(ref)s. Amount: %(amount)s. Contract set to: In Progress, Next Invoice: %(inv)s. Email sent to customer.',
                    ref=transaction._get_html_link(title=transaction.reference),
                    amount=transaction.amount,
                    inv=self.next_invoice_date,
                )
            else:
                msg_body = _(
                    'Manual payment succeeded. Payment reference: %(ref)s. Amount: %(amount)s. Contract set to: In Progress, Next Invoice: %(inv)s. Email sent to customer.',
                    ref=transaction._get_html_link(title=transaction.reference),
                    amount=transaction.amount,
                    inv=self.next_invoice_date,
                )
            self.message_post(body=msg_body)
            if invoice.state != 'posted':
                invoice.with_context(ocr_trigger_delta=15)._post()
