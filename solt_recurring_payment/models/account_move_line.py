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

    def _sale_determine_order(self):
        """Override to exclude subscription invoice lines from sale order mapping."""
        mapping_from_invoice = super()._sale_determine_order()
        # Remove lines that belong to subscriptions (handled separately)
        if mapping_from_invoice:
            aml_ids_to_remove = [
                aml_id for aml_id, so in mapping_from_invoice.items()
                if self.browse(aml_id).subscription_id
            ]
            for aml_id in aml_ids_to_remove:
                del mapping_from_invoice[aml_id]
        return mapping_from_invoice
