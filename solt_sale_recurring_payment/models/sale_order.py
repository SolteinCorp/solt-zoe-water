# -*- coding: utf-8 -*-
# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "solt.recurring.order.mixin"]

    def _action_confirm(self):
        """Create subscriptions on sale order confirmation."""
        result = super()._action_confirm()
        self._create_subscriptions()
        return result

    def _action_cancel(self):
        """Delete draft subscriptions on sale order cancellation."""
        result = super()._action_cancel()
        self.subscription_ids.filtered(lambda subscription: subscription.state == "draft").unlink()
        return result

    def _prepare_subscription_values(self, plan_id, start_date, lines):
        """Get additional values for sale order subscription."""
        values = super()._prepare_subscription_values(plan_id, start_date, lines)
        values.update(
            {
                "type": "sale",
                "pricelist_id": self.pricelist_id.id,
                "journal_id": self.journal_id.id,
            }
        )
        return values

    def _get_recurring_order_line(self):
        """Excluir líneas que ya están vinculadas a una suscripción.

        Cuando una orden de venta es generada desde el ciclo de facturación de una
        suscripción (productos almacenables), sus líneas ya tienen subscription_id
        asignado. Al confirmar esa orden, _create_subscriptions() no debe crear
        suscripciones duplicadas a partir de esas líneas.
        """
        return super()._get_recurring_order_line().filtered(
            lambda line: not line.subscription_id
        )

    def _get_invoiceable_lines(self, final=False):
        """Filter out subscription lines that are not yet due for invoicing."""
        lines = super()._get_invoiceable_lines(final=final)
        return lines.filtered(lambda line: not line.subscription_id or not line.start_recurring_date or line.start_recurring_date == self.date_order)

    def _get_name_tax_totals_view(self):
        """Return the subscription period total view for subscription orders."""
        self.ensure_one()
        return "solt_recurring_payment.subscription_period_total" if self.is_subscription else super()._get_name_tax_totals_view()
