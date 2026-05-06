# -*- coding: utf-8 -*-
from odoo import _, fields, models


class SoltSaleSubscriptionCloseWizard(models.TransientModel):
    _name = "solt.subscription.close.wizard"
    _description = 'Subscription Close Wizard'

    subscription_id = fields.Many2one(
        'solt.subscription',
        string='Subscription',
        required=True,
        default=lambda self: self.env.context.get('active_id'),
        help='The subscription to be closed',
    )
    close_reason_id = fields.Many2one(
        'solt.subscription.close.reason',
        string='Close Reason',
        required=True,
        help='Select the reason for closing this subscription',
    )
    closing_note = fields.Text(
        string='Additional Notes',
        help='Optional notes to add regarding the closure of this subscription',
    )

    def action_close(self):
        """Close the subscription with the selected reason."""
        self.ensure_one()

        if self.closing_note:
            self.subscription_id.message_post(
                body=_("Closing note: %s", self.closing_note)
            )

        self.subscription_id.set_close(close_reason_id=self.close_reason_id.id)

        return {'type': 'ir.actions.act_window_close'}
