# -*- coding: utf-8 -*-
from odoo import Command, models


class SoltSaleSubscriptionLine(models.Model):
    _inherit = "solt.subscription.line"

    def _prepare_invoice_line(self):
        """Prepare invoice line values for this subscription line."""
        res = super()._prepare_invoice_line()
        if self.subscription_id.type == "sale" and self.origin_line_id:
            res["sale_line_ids"] = [Command.set(self.origin_line_id.ids)]
        return res
