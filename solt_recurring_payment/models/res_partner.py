# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    subscription_count = fields.Integer(
        string='Subscriptions',
        compute='_compute_subscription_count',
        help='Number of recurring subscriptions (active or closed) linked to this partner and its children.'
    )

    def write(self, vals):
        """
        Override of the write method to prevent archiving a partner
        if they are linked to active recurring subscriptions.

        Args:
            vals (dict): The values to write on the record.

        Raises:
            ValidationError: If attempting to archive a partner with active subscriptions.

        Returns:
            bool: Result of the super().write(vals) call.
        """
        res = super().write(vals)
        if 'active' in vals and not vals.get('active'):
            Subscription = self.env['solt.subscription']
            order_ids = Subscription.sudo().search([
                ('state', '=', 'active'),
                ('partner_id', 'in', self.ids),
            ])
            if order_ids:
                contract_str = ", ".join(order_ids.mapped('name'))
                raise ValidationError(_("You can't archive the partner as it is used in the following recurring orders: %s", contract_str))
        return res

    def _compute_subscription_count(self):
        all_partners_subquery = self.with_context(active_test=False)._search([('id', 'child_of', self.ids)])
        subscription_data = self.env['solt.subscription']._read_group(
            domain=[('partner_id', 'in', all_partners_subquery), ('state', 'in', ['active', 'closed'])],
            groupby=['partner_id'], aggregates=['__count'],
        )
        self.subscription_count = 0
        for partner, count in subscription_data:
            while partner:
                if partner in self:
                    partner.subscription_count += count
                partner = partner.with_context(prefetch_fields=False).parent_id

    def open_related_subscription(self):
        """
        Opens the related subscription(s) for the current partner.

        - If there is only one related subscription, opens its form view.
        - If there are multiple, opens a tree view listing all.
        - Only includes subscriptions in 'active' or 'closed' state.
        - The context sets default and search values for the partner.

        Returns:
            dict: An Odoo action dictionary to open the appropriate view.
        """
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "res_model": "solt.subscription",
            "name": _("Partner Subscription"),
            "domain": [('state', 'in', ['active', 'closed'])],
            "context": {
                'search_default_partner_id': [self.id],
                'default_partner_id': self.id,
            }
        }
        all_partners = self.with_context(active_test=False).search([('id', 'child_of', self.ids)])

        subscription_ids = self.env['solt.subscription'].search_read(
            domain=[('partner_id', 'in', all_partners.ids), ('state', 'in', ['active', 'closed'])],
            fields=['id']
        )
        if len(subscription_ids) == 1:
            action['res_id'] = subscription_ids[0]['id']
            action['views'] = [(False, 'form')]
        else:
            action['views'] = [(False, 'list'), (False, 'form')]
        return action
