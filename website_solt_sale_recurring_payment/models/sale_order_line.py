# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _is_reorder_allowed(self):
        """Prevent reordering of subscription lines (they renew automatically)."""
        if self.recurring_ok:
            return False
        return super()._is_reorder_allowed()
