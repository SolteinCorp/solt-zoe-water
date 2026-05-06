# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    subscription_id = fields.Many2one(
        "solt.subscription",
        string='Subscription',
        index=True,
        help='Reference to the related subscription for this invoice line.'
    )
