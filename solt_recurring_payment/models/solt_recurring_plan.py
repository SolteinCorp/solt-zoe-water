# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import Command, _, _lt, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import get_timedelta


class SoltSaleRecurringPlan(models.Model):
    _name = 'solt.recurring.plan'
    _description = 'Recurring Payment Plan'

    active = fields.Boolean(
        default=True,
        string="Active",
        help="Indicates whether the recurring plan is active. Inactive plans are not available for new subscriptions."
    )
    name = fields.Char(
        translate=True,
        required=True,
        default="Monthly",
        string="Name",
        help="The name of the recurring payment plan, e.g., 'Monthly', 'Annual'."
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        help="The company to which this recurring plan belongs."
    )

    # Billing Period, use billing_period property for access to the timedelta
    billing_period_value = fields.Integer(
        string="Duration",
        required=True,
        default=1,
        help="Number of periods between each billing cycle"
    )
    billing_period_unit = fields.Selection(
        [("day", "Days"), ("week", "Weeks"), ("month", "Months"), ('year', 'Years')],
        string="Unit",
        required=True,
        default='month',
        help="Time unit for the billing period (days, weeks, months, or years)"
    )

    billing_period_display = fields.Char(
        compute='_compute_billing_period_display',
        string="Billing Period",
        help="Billing Period",
    )
    billing_period_display_sentence = fields.Char(
        compute='_compute_billing_period_display_sentence',
        string="Billing Period Display",
        help="Billing Period Display",
    )

    # Self Service
    user_closable = fields.Boolean(string="Closable", default=False,
                                   help="Customer can close their subscriptions.")
    user_extend = fields.Boolean(string="Renew", default=False,
                                 help="Customer can create a renewal quotation for their subscription.")
    related_plan_ids = fields.Many2many("solt.recurring.plan", "solt_recurring_plan_related_plan",
                                       "plan_id", "related_plan_id", string="Optional Plans",
                                        help="Allow your customers to switch from this plan to "
                                            "another on quotation (new subscription or renewal)")
    # Invoicing
    auto_close_limit = fields.Integer(string="Automatic Closing", default=15,
                                      help="Unpaid subscription after the due date majored by this number of days will be automatically closed by "
                                           "the subscriptions expiration scheduled action. \n"
                                           "If the chosen payment method has failed to renew the subscription after this time, "
                                           "the subscription is automatically closed.")
    auto_close_limit_display = fields.Char(
        string="Automatic Closing After",
        compute="_compute_auto_close_limit_display",
        help="Automatic Closing After",
    )
    auto_archive_delay = fields.Integer(
        string="Automatic Archiving",
        default=15,
        help="Number of days after a subscription is closed before it is automatically archived. "
             "Archived subscriptions are hidden from default views and can be permanently deleted.",
    )
    auto_archive_delay_display = fields.Char(
        string="Automatic Archiving After",
        compute="_compute_auto_archive_delay_display",
        help="Automatic Archiving After",
    )
    invoice_mail_template_id = fields.Many2one('mail.template', string='Invoice Email Template',
                                               domain=[('model', '=', 'account.move')],
                                               default=lambda self: self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False),
                                               help="Email template used to send invoicing email automatically.\n"
                                                    "Leave it empty if you don't want to send email automatically.")

    product_subscription_pricing_ids = fields.One2many(
        'solt.recurring.pricing',
        'plan_id',
        string="Recurring Pricing",
        domain=['|', ('product_template_id', '=', None), ('product_template_id.active', '=', True)],
        help="Recurring pricing related to this plan.",
    )
    # UX
    active_subs_count = fields.Integer(
        compute="_compute_active_subs_count",
        string="Subscriptions",
        help="Number of active subscriptions for this plan."
    )

    def write(self, values):
        """Override write to maintain bidirectional relationship between related plans.

        When related_plan_ids is updated, ensure the inverse relationship is also updated
        by adding/removing the current plan from the related plans' related_plan_ids field.
        """
        if "related_plan_ids" in values:
            old_related = {plan.id: plan.related_plan_ids for plan in self}
        res = super().write(values)
        if "related_plan_ids" in values:
            for plan in self:
                if to_remove := old_related[plan.id] - plan.related_plan_ids:
                    to_remove.related_plan_ids = [Command.unlink(plan.id)]
                if to_add := plan.related_plan_ids - old_related[plan.id]:
                    to_add.related_plan_ids = [Command.link(plan.id)]
        return res

    def _compute_active_subs_count(self):
        self.active_subs_count = 0
        res = self.env['solt.subscription'].read_group(
            [('plan_id', 'in', self.ids), ('state', '=', 'active')],
            ['__count'], ['plan_id'],
        )
        for template in res:
            if template['plan_id']:
                self.browse(template['plan_id'][0]).active_subs_count = template['plan_id_count']

    def action_open_active_sub(self):
        """Open a view showing all active subscriptions for this plan.

        Returns:
            dict: Action dictionary to display active subscriptions in tree and form views.
        """
        return {
            'name': _('Subscriptions'),
            'view_mode': 'tree,form',
            'domain': [('plan_id', 'in', self.ids), ('state', '=', 'active')],
            'res_model': 'solt.subscription',
            'type': 'ir.actions.act_window',
        }

    @property
    def billing_period(self):
        """Get the billing period as a timedelta object.

        Returns:
            timedelta or False: The billing period calculated from billing_period_value
            and billing_period_unit, or False if either value is not set.
        """
        if not self.billing_period_unit or not self.billing_period_value:
            return relativedelta()
        return get_timedelta(self.billing_period_value, self.billing_period_unit)

    @api.depends('billing_period_value', 'billing_period_unit')
    def _compute_billing_period_display(self):
        labels = dict(self._fields['billing_period_unit']._description_selection(self.env))
        for plan in self:
            plan.billing_period_display = f"{plan.billing_period_value} {labels[plan.billing_period_unit]}"

    @api.depends('billing_period_value', 'billing_period_unit')
    def _compute_billing_period_display_sentence(self):
        for plan in self:
            value = plan.billing_period_value
            if plan.billing_period_unit == 'day':
                sentence = _('per %d days', value) if value > 1 else _('per day')
            elif plan.billing_period_unit == 'week':
                sentence = _('per %d weeks', value) if value > 1 else _('per week')
            elif plan.billing_period_unit == 'month':
                sentence = _('per %d months', value) if value > 1 else _('per month')
            elif plan.billing_period_unit == 'year':
                sentence = _('per %d years', value) if value > 1 else _('per year')
            else:
                raise ValueError(f"Invalid Billing Period Unit {plan.billing_period_unit!r}")
            plan.billing_period_display_sentence = sentence

    @api.depends('auto_close_limit')
    def _compute_auto_close_limit_display(self):
        for plan in self:
            plan.auto_close_limit_display = _lt('%s days', plan.auto_close_limit)

    @api.depends('auto_archive_delay')
    def _compute_auto_archive_delay_display(self):
        for plan in self:
            plan.auto_archive_delay_display = _lt('%s days', plan.auto_archive_delay)

    @api.constrains('billing_period_value')
    def _check_not_zero_billing_period(self):
        for plan in self:
            if plan.billing_period_value < 1:
                raise ValidationError(
                    _('Recurring period must be a positive number. Please ensure the input is a valid positive numeric value.')
                )
