# -*- coding: utf-8 -*-
import logging

from odoo import Command, _, api, fields, models

_logger = logging.getLogger(__name__)


class SoltSubscription(models.Model):
    _inherit = "solt.subscription"

    sale_order_ids = fields.Many2many(
        comodel_name="sale.order",
        string="Sale Orders",
        compute="_compute_sale_order_ids",
        help="Sale orders generated from this subscription billing cycles.",
    )
    sale_order_count = fields.Integer(
        string="Sale Order Count",
        compute="_compute_sale_order_ids",
        help="Number of sale orders generated from this subscription billing cycles.",
    )

    @api.depends("subscription_line_ids", "origin_id")
    def _compute_sale_order_ids(self):
        """Compute sale orders generated from this subscription's billing cycles.

        Searches sale.order.line records whose subscription_id matches this
        subscription. Excludes the origin document when it is a sale.order
        (origin_id can be either sale.order or purchase.order).
        """
        all_subscription_ids = self.ids
        if not all_subscription_ids:
            self.sale_order_ids = False
            self.sale_order_count = 0
            return

        sale_order_lines = self.env["sale.order.line"].search(
            [
                ("subscription_id", "in", all_subscription_ids),
            ]
        )
        subscription_to_sale_order_ids = {}
        for sale_order_line in sale_order_lines:
            subscription_id = sale_order_line.subscription_id.id
            subscription_to_sale_order_ids.setdefault(subscription_id, set())
            subscription_to_sale_order_ids[subscription_id].add(sale_order_line.order_id.id)

        for subscription in self:
            all_linked_ids = subscription_to_sale_order_ids.get(subscription.id, set())
            origin = subscription.origin_id
            if origin and origin._name == "sale.order":
                all_linked_ids -= {origin.id}
            subscription.sale_order_ids = list(all_linked_ids)
            subscription.sale_order_count = len(all_linked_ids)

    def action_view_generated_sale_orders(self):
        """Open the sale orders created from this subscription billing cycles."""
        self.ensure_one()
        sale_order_action = self.env["ir.actions.act_window"]._for_xml_id("sale.action_quotations_with_onboarding")
        if self.sale_order_count == 1:
            sale_order_action["views"] = [
                (self.env.ref("sale.view_order_form").id, "form"),
            ]
            sale_order_action["res_id"] = self.sale_order_ids.id
        else:
            sale_order_action["domain"] = [
                ("id", "in", self.sale_order_ids.ids),
            ]
        return sale_order_action

    def _is_storable_product(self, product):
        """Return True if the product is storable (tracks inventory).

        Odoo 18 removed the ``'product'`` value from ``product.type``. The
        storable flag now lives on the Boolean ``is_storable`` field added by
        the ``stock`` module. Since this module does not depend on ``stock``,
        we guard the access with ``hasattr``: if the field is not present
        (i.e. ``stock`` is not installed), nothing is storable.
        """
        if not product:
            return False
        return bool(getattr(product, "is_storable", False))

    def _has_storable_subscription_lines(self):
        """Return True if at least one subscription line has a storable product."""
        return any(self._is_storable_product(line.product_id) for line in self.subscription_line_ids)

    def _prepare_sale_order_values(self):
        """Prepara el dict de valores para crear una sale.order en estado borrador.

        La fecha de la orden (date_order) es un campo Datetime, por lo que se convierte
        desde next_invoice_date (fields.Date) usando fields.Datetime.to_datetime().
        """
        self.ensure_one()
        billing_datetime = fields.Datetime.to_datetime(self.next_invoice_date or fields.Date.today())
        return {
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "pricelist_id": self.pricelist_id.id if self.pricelist_id else False,
            "date_order": billing_datetime,
            "origin": self.name,
            "user_id": self.user_id.id,
            "fiscal_position_id": self.fiscal_position_id.id if self.fiscal_position_id else False,
            "payment_term_id": self.payment_term_id.id if self.payment_term_id else False,
            "order_line": [],
        }

    def _prepare_sale_order_line_values(self, subscription_line):
        """Prepara el dict de valores para una línea de sale.order.

        Usa product.taxes_id (impuestos de venta definidos en el producto) filtrados
        por compañía, a diferencia de product.supplier_taxes_id que son para compras.

        El precio se toma directamente de la línea de suscripción, ya que fue calculado
        originalmente desde la lista de precios al crear la suscripción.
        """
        self.ensure_one()
        product = subscription_line.product_id
        applicable_sale_taxes = product.taxes_id.filtered(lambda tax: tax.company_id == self.company_id)

        return {
            "product_id": product.id,
            "plan_id": self.plan_id.id,
            "name": subscription_line.name,
            "product_uom_qty": subscription_line.product_uom_qty,
            "product_uom": subscription_line.product_uom_id.id,
            "price_unit": subscription_line.price_unit,
            "tax_id": [Command.set(applicable_sale_taxes.ids)],
            "subscription_id": self.id,
        }

    def _create_sale_order_for_subscription(self):
        """Crea y confirma una orden de venta desde la suscripción.

        La OV se crea y confirma para que sale_stock genere el picking de envío.
        Las líneas de la OV llevan subscription_id para trazabilidad y para que
        _get_recurring_order_line() las excluya al confirmar (evita suscripciones
        duplicadas).

        Retorna la sale.order creada y confirmada.
        """
        self.ensure_one()
        sale_order_values = self._prepare_sale_order_values()
        sale_order_line_values_list = []

        for subscription_line in self.subscription_line_ids:
            line_values = self._prepare_sale_order_line_values(subscription_line)
            sale_order_line_values_list.append(Command.create(line_values))

        sale_order_values["order_line"] = sale_order_line_values_list
        new_sale_order = self.env["sale.order"].sudo().create(sale_order_values)
        new_sale_order.sudo().action_confirm()

        _logger.info(
            "Orden de venta '%s' creada y confirmada desde suscripción '%s'.",
            new_sale_order.name,
            self.name,
        )
        return new_sale_order

    # === CANCELLATION HOOKS === #

    def _cancel_pending_future_shipments(self):
        """Cancel pending stock pickings linked to sale orders of this subscription.

        Pickings already done are left untouched (they were shipped). Anything
        in waiting/confirmed/assigned/draft is cancelled so future periods do not
        ship. SOs themselves are not cancelled — only their non-delivered pickings.
        """
        super()._cancel_pending_future_shipments()
        for subscription in self:
            pending_pickings = subscription.sale_order_ids.picking_ids.filtered(
                lambda picking: picking.state not in ("done", "cancel")
            )
            if pending_pickings:
                pending_pickings.sudo().action_cancel()
                _logger.info(
                    "Cancelled %d pending picking(s) for subscription '%s'.",
                    len(pending_pickings),
                    subscription.name,
                )
        return True

    def _create_bulk_remaining_shipment(self):
        """Create one final sale order shipping all remaining storable goods at once.

        Iterates non-downpayment storable lines and multiplies the per-period
        quantity by ``prepaid_periods_remaining``. ``price_unit`` is forced to 0
        because the customer already paid the prepaid invoice. The created
        sale.order is confirmed so ``sale_stock`` generates the bulk picking.
        """
        super()._create_bulk_remaining_shipment()
        new_sale_orders = self.env["sale.order"]
        for subscription in self:
            if subscription.type != "sale" or not subscription.is_prepaid:
                continue
            remaining_periods = int(subscription.prepaid_periods_remaining or 0)
            if remaining_periods <= 0:
                continue
            storable_lines = subscription.subscription_line_ids.filtered(
                lambda sub_line: subscription._is_storable_product(sub_line.product_id) and not sub_line.is_downpayment
            )
            if not storable_lines:
                continue

            sale_order_values = subscription._prepare_sale_order_values()
            sale_order_values["origin"] = _("%s - Final bulk shipment", subscription.name)
            order_line_commands = []
            for sub_line in storable_lines:
                line_values = subscription._prepare_sale_order_line_values(sub_line)
                line_values["product_uom_qty"] = sub_line.product_uom_qty * remaining_periods
                line_values["price_unit"] = 0.0
                line_values["name"] = _(
                    "%(product)s - Remaining %(periods)s period(s) shipped together",
                    product=sub_line.product_id.display_name,
                    periods=remaining_periods,
                )
                order_line_commands.append(Command.create(line_values))
            sale_order_values["order_line"] = order_line_commands

            new_so = self.env["sale.order"].sudo().create(sale_order_values)
            new_so.sudo().action_confirm()
            new_sale_orders |= new_so
            _logger.info(
                "Bulk shipment sale order '%s' created for subscription '%s' (%d periods, %d storable lines).",
                new_so.name,
                subscription.name,
                remaining_periods,
                len(storable_lines),
            )
        return new_sale_orders

    def _create_invoices(self, final=False):
        """Override para crear OV antes de facturar suscripciones con productos almacenables.

        Para suscripciones type='sale' con al menos un producto almacenable:
          1. Crea una sale.order con todas las líneas de la suscripción.
          2. Confirma la sale.order → sale_stock genera el picking de envío.
          3. Delega a super() para crear la factura normalmente.

        La factura se crea desde la suscripción (no desde la OV). El flujo posterior
        del cron (_handle_automatic_invoices) se encarga de:
          - Publicar la factura (action_post).
          - Procesar el pago automático si hay payment_token.
          - Confirmar la suscripción y avanzar next_invoice_date (en _post()).
        """
        sale_subscriptions_with_storable = self.filtered(
            lambda subscription: subscription.type == "sale" and subscription._has_storable_subscription_lines()
        )

        for subscription in sale_subscriptions_with_storable:
            if subscription.partner_id.lang:
                subscription = subscription.with_context(lang=subscription.partner_id.lang)
            subscription = subscription.with_company(subscription.company_id)
            subscription._create_sale_order_for_subscription()

        # Crear facturas para TODAS las suscripciones (incluyendo las que generaron OV).
        # El flujo normal del cron maneja la publicación y el pago automático.
        return super()._create_invoices(final=final)
