# -*- coding: utf-8 -*-
from odoo import fields, models


class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    plan_id = fields.Many2one(
        'solt.recurring.plan',
        string='Subscription Plan',
        index=True,
        ondelete='cascade',
        help="If set, this rule only applies to subscription lines using this plan. "
             "Leave empty for plan-agnostic rules (also applied to non-recurring lines).",
    )
