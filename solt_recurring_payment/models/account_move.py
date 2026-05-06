# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    subscription_ids = fields.Many2many(
        'solt.subscription',
        compute='_compute_subscription_count',
        string='Subscriptions',
        readonly=True,
        store=True,
        copy=False,
        help="Subscriptions linked to this invoice through invoice lines",
    )
    subscription_count = fields.Integer(
        string='Subscription Count',
        compute='_compute_subscription_count',
        readonly=True,
        store=True,
        copy=False,
        help="Number of subscriptions associated with this invoice",
    )
    is_recurring_document = fields.Boolean(
        string='Recurring Document',
        compute='_compute_subscription_count',
        store=True,
        copy=False,
        help="Indicates this document was generated from a recurring subscription.",
    )

    @api.depends('line_ids.subscription_id')
    def _compute_subscription_count(self):
        for move in self:
            subscription_ids = tuple(set(move.line_ids.subscription_id.ids))
            move.subscription_ids = subscription_ids
            move.subscription_count = len(subscription_ids)
            move.is_recurring_document = bool(subscription_ids)

    def _post(self, soft=True):
        posted_moves = super()._post(soft=soft)
        for move in posted_moves:
            subscription_lines = move.invoice_line_ids.filtered('subscription_id')
            if not subscription_lines:
                continue
            subscriptions = subscription_lines.mapped('subscription_id')
            if 'refund' in move.move_type:
                for subscription in subscriptions:
                    body = _("The following refund %s has been made on this subscription.", move._get_html_link())
                    subscription.message_post(body=body)
                continue
            for subscription in subscriptions:
                if subscription.state == 'draft':
                    subscription.action_confirm()
                if move.invoice_date == subscription.next_invoice_date:
                    subscription._update_next_invoice_date()
        return posted_moves

    def _message_auto_subscribe_followers(self, updated_values, subtype_ids):
        """Prevent assignment emails for subscription invoices."""
        res = super()._message_auto_subscribe_followers(updated_values, subtype_ids)
        user_id = updated_values.get('user_id')
        if user_id:
            subscriptions = self.invoice_line_ids.mapped('subscription_id')
            if subscriptions:
                salespersons = subscriptions.mapped('user_id')
                if salespersons and user_id in salespersons.ids and user_id != self.env.user.id:
                    partner_ids = salespersons.partner_id.ids
                    res = [(v[0], v[1], False) for v in res if v[0] in partner_ids and v[2] == 'mail.message_user_assigned']
        return res

    def action_view_subscriptions(self):
        """Action to view related subscriptions."""
        self.ensure_one()
        action = self.env.ref('solt_recurring_payment.solt_subscription_action')._get_action_dict()
        subscriptions = self.subscription_ids
        if len(subscriptions) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = subscriptions.id
        else:
            action['domain'] = [('id', 'in', subscriptions.ids)]
        return action
