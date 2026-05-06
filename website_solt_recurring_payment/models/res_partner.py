from collections import defaultdict

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def next_recurring_payment_subscription(self):
        """
        Returns the next recurring payment subscription for the current user.

        This method searches for a `solt.subscription` record associated with the current user's
        partner or commercial partner, where the subscription state is either 'active' or 'closed'.
        The result is ordered by the next invoice date in ascending order, and only the first match is returned.

        Returns:
            recordset: The next `solt.subscription` record, or an empty recordset if none found.
        """
        self.ensure_one()
        partner_ids = [self.env.user.partner_id.id, self.env.user.partner_id.commercial_partner_id.id]
        domain = [
            ('partner_id', 'in', partner_ids),
            ('state', 'in', ['active', 'closed']),
        ]
        return self.env['solt.subscription'].search(domain, limit=1, order='next_invoice_date asc')

    def all_subscriptions_total_amount(self) -> dict:
        """
        Calculates the total recurring amount for all subscriptions of the current user,
        grouped by currency.

        This method searches for all `solt.subscription` records associated with the
        current user's partner or commercial partner, where the subscription state is either
        'active' or 'closed'. It sums the `recurring_total` for each currency.

        Returns:
            dict: A dictionary mapping currency records to the total recurring amount.
        """
        self.ensure_one()
        partner_ids = [self.env.user.partner_id.id, self.env.user.partner_id.commercial_partner_id.id]
        domain = [
            ('partner_id', 'in', partner_ids),
            ('state', 'in', ['active', 'closed']),
        ]
        result = defaultdict(float)
        for subscription in self.env['solt.subscription'].search(domain):
            result[subscription.currency_id] += subscription.recurring_total
        return result
