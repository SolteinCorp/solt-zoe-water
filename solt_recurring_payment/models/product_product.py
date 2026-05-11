# -*- coding: utf-8 -*-
from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_best_subscription_pricing_rule(self, **kwargs):
        """ Return the pricing rule for the given duration.
        :param float duration: duration, in unit uom
        :param str unit: duration unit (hour, day, week)
        :return: pricing matching the duration/unit pair, or empty recordset
        """
        self.ensure_one()

        duration, unit = kwargs.get('duration', False), kwargs.get('unit', '')

        if not self.recurring_ok or not duration or not unit:
            return self.env['solt.recurring.pricing']

        for pricing in self.product_subscription_pricing_ids:
            if pricing.plan_id.billing_period_value != duration or pricing.plan_id.billing_period_unit != unit:
                continue
            if not pricing._applies_to(self):
                continue
            return pricing
        return self.env['solt.recurring.pricing']
