# -*- coding: utf-8 -*-
import logging

from odoo import Command, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "solt.recurring.order.mixin"]

    def _action_confirm(self):
        res = super()._action_confirm()
        self._create_subscriptions()
        return res

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Split prepaid invoice lines into ``(first period, downpayment for
        remaining N-1 periods)`` so the journal entry of the origin invoice
        recognises only the first month as revenue and parks the rest in the
        customer advance account. Mirrors ``sale.advance.payment.inv``'s
        accounting (uses the product's category ``downpayment`` account).
        """
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        for move in moves.filtered(lambda m: m.state == "draft"):
            downpayment_commands = []
            for inv_line in move.invoice_line_ids:
                if not inv_line.sale_line_ids:
                    continue
                origin_line = inv_line.sale_line_ids[:1]
                periods = origin_line._get_prepaid_periods_for_invoice()
                if periods <= 1:
                    continue
                downpayment_vals = origin_line._prepare_invoice_downpayment_line(
                    inv_line=inv_line, periods=periods,
                )
                if downpayment_vals:
                    downpayment_commands.append(Command.create(downpayment_vals))
            if downpayment_commands:
                move.write({"invoice_line_ids": downpayment_commands})
        return moves

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

    def _get_max_prepaid_periods(self):
        """Return the largest ``required_recurring_quantity`` among prepaid lines
        on this order, or 1 if no prepaid line is present. Used to scale the
        delivery line so the customer pays for the shipments covering the full
        prepaid commitment.
        """
        self.ensure_one()
        max_periods = 1
        for line in self.order_line:
            pricing = line._get_prepaid_pricing() if hasattr(line, "_get_prepaid_pricing") else None
            if pricing and pricing.required_recurring_quantity > 1:
                max_periods = max(max_periods, pricing.required_recurring_quantity)
        return max_periods

    # NOTE: the delivery line is created with the standard per-shipment qty=1.
    # The N-period expansion (so the customer pays the prepaid commitment
    # upfront) is applied at the tax-computation layer for the SO total, and
    # split into a regular line + a downpayment line at invoice time. See
    # ``sale.order.line._prepare_base_line_for_taxes_computation`` and the
    # ``_create_invoices`` override below.
