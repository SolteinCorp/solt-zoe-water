# -*- coding: utf-8 -*-
from odoo import Command, models


class SoltSaleSubscriptionLine(models.Model):
    _inherit = "solt.subscription.line"

    def _prepare_invoice_line(self, quantity=None):
        """Prepare invoice line values for the sale-side cron invoices.

        - Link the line back to its origin sale.order.line.
        - For downpayment subscription lines (the monthly negative line that
          consumes the prepaid balance), route the line to the same customer
          advance account that the SO origin invoice used. Without this the
          negative line would credit the regular sales account and the
          customer advance balance would never be consumed.
        """
        invoice_line_values = super()._prepare_invoice_line(quantity=quantity)
        if self.subscription_id.type == "sale" and self.origin_line_id:
            invoice_line_values["sale_line_ids"] = [Command.set(self.origin_line_id.ids)]
        if self.is_downpayment and self.product_id:
            product_account = self.product_id.product_tmpl_id.get_product_accounts(
                fiscal_pos=self.subscription_id.fiscal_position_id,
            )
            account = product_account.get("downpayment") or product_account.get("income")
            if account:
                invoice_line_values["account_id"] = account.id if hasattr(account, "id") else account
        return invoice_line_values
