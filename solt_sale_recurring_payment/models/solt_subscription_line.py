# -*- coding: utf-8 -*-
from odoo import Command, models


class SoltSaleSubscriptionLine(models.Model):
    _inherit = "solt.subscription.line"

    def _prepare_invoice_line(self, quantity=None):
        """Prepare invoice line values and link origin sale order line for sale subscriptions."""
        invoice_line_values = super()._prepare_invoice_line(quantity=quantity)
        if self.subscription_id.type == "sale" and self.origin_line_id:
            invoice_line_values["sale_line_ids"] = [Command.set(self.origin_line_id.ids)]
        return invoice_line_values
