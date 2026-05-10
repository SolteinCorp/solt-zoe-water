# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "solt.recurring.order.mixin"]

    def _action_confirm(self):
        res = super()._action_confirm()
        self._create_subscriptions()
        return res

    def _action_cancel(self):
        res = super()._action_cancel()
        self.subscription_ids.filtered(lambda s: s.state == "draft").unlink()
        return res

    def _prepare_subscription_values(self, plan_id, lines):
        """Get additional values for sale order subscription."""
        values = super()._prepare_subscription_values(plan_id, lines)
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
        return super()._get_recurring_order_line().filtered(lambda line: not line.subscription_id)

    def _get_invoiceable_lines(self, final=False):
        """Return invoiceable lines, removing only:
          - Lines from cron-generated monthly SOs (subscription_id set AND the
            current SO is not the subscription's origin); the cron handles their
            invoicing from the subscription itself.
          - Lines whose free_periods window has not elapsed yet (the subscription
            checks per line at invoicing time).

        Lines on the original SO always pass: the first invoice (with qty
        expanded for prepaid pricings) is generated from the SO origin like in
        the standard Odoo flow.
        """
        parent_lines = super()._get_invoiceable_lines(final=final)
        subscription_lines_to_remove = parent_lines.filtered(
            lambda ln: not ln.display_type and ln.recurring_ok and (
                (ln.subscription_id and ln.order_id != ln.subscription_id.origin_id)
                or ln.free_periods > 0
            )
        )
        if not subscription_lines_to_remove:
            return parent_lines

        remaining_lines = (parent_lines - subscription_lines_to_remove).sorted("sequence")

        sections_with_products = set()
        current_section_id = None
        for line in remaining_lines:
            if line.display_type == "line_section":
                current_section_id = line.id
            elif not line.display_type and current_section_id is not None:
                sections_with_products.add(current_section_id)

        kept_line_ids = []
        current_section_active = True
        for line in remaining_lines:
            if line.display_type == "line_section":
                current_section_active = line.id in sections_with_products
                if current_section_active:
                    kept_line_ids.append(line.id)
            elif line.display_type == "line_note":
                if current_section_active:
                    kept_line_ids.append(line.id)
            else:
                kept_line_ids.append(line.id)

        return self.env["sale.order.line"].browse(kept_line_ids)

    def _get_name_tax_totals_view(self):
        self.ensure_one()
        return "solt_recurring_payment.subscription_period_total" if self.is_subscription else super()._get_name_tax_totals_view()
