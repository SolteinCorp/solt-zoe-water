# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class SoltSaleSubscriptionCloseWizard(models.TransientModel):
    _name = "solt.subscription.close.wizard"
    _description = 'Subscription Cancel Wizard'

    subscription_id = fields.Many2one(
        'solt.subscription',
        string='Subscription',
        required=True,
        default=lambda self: self.env.context.get('active_id'),
        help='The subscription to be cancelled',
    )
    close_reason_id = fields.Many2one(
        'solt.subscription.close.reason',
        string='Cancellation Reason',
        required=True,
        help='Select the reason for cancelling this subscription',
    )
    closing_note = fields.Text(
        string='Additional Notes',
        help='Optional notes to add regarding the cancellation of this subscription',
    )
    is_prepaid = fields.Boolean(
        related='subscription_id.is_prepaid',
        readonly=True,
        help='True when the subscription has a downpayment (prepaid) component. '
             'Only prepaid subscriptions can choose refund or bulk-shipment modes.',
    )
    cancel_mode = fields.Selection(
        selection=[
            ('honor', 'Honor paid period (keep deliveries until prepaid is consumed)'),
            ('refund', 'Cancel now and refund pending prepaid periods'),
            ('bulk_ship', 'Cancel now and ship all remaining products at once'),
        ],
        string='Cancellation Method',
        default='honor',
        required=True,
        help='How to handle the cancellation. Refund and bulk-ship only apply to prepaid subscriptions.',
    )

    @api.onchange('subscription_id')
    def _onchange_subscription_id(self):
        """Force honor mode when the subscription is not prepaid."""
        if self.subscription_id and not self.subscription_id.is_prepaid:
            self.cancel_mode = 'honor'

    def action_close(self):
        """Cancel the subscription using the selected mode."""
        self.ensure_one()
        self.subscription_id.action_cancel_subscription(
            cancel_mode=self.cancel_mode,
            close_reason_id=self.close_reason_id.id,
            closing_note=self.closing_note,
        )
        return {'type': 'ir.actions.act_window_close'}
