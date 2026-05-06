# -*- coding: utf-8 -*-
from odoo import fields, models


class Pricelist(models.Model):
    _inherit = "product.pricelist"

    product_subscription_pricing_ids = fields.One2many(
        'solt.recurring.pricing',
        'pricelist_id',
        string="Recurring Pricing",
        domain=[
            '|', ('product_template_id', '=', None), ('product_template_id.active', '=', True),
        ],
        copy=True,
        help="Subscription pricing rules associated with this pricelist",
    )
