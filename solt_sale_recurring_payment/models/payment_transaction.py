# -*- coding: utf-8 -*-
# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from datetime import datetime, time, timedelta

from odoo import api, fields, models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    subscription_ids = fields.Many2many(
        comodel_name="solt.subscription",
        compute="_compute_subscriptions",
        string="Subscriptions",
        copy=False,
        help="Subscriptions related to this payment transaction via sale orders or invoices",
    )
    renewal_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("authorized", "Authorized"),
            ("cancel", "Refused"),
        ],
        string="Renewal State",
        compute="_compute_renewal_state",
        help="State of the payment transaction for subscription renewal purposes",
    )
    subscription_action = fields.Selection(
        selection=[
            ("automatic_send_mail", "Send Mail (automatic payment)"),
            ("manual_send_mail", "Send Mail (manual payment)"),
            ("assign_token", "Assign Token"),
        ],
        string="Subscription Action",
        default="assign_token",
        help="Action of the payment transaction for subscription renewal purposes",
    )

    @api.depends("sale_order_ids.subscription_ids", "invoice_ids.subscription_ids")
    def _compute_subscriptions(self):
        """Compute subscriptions linked to this transaction via sale orders or invoices."""
        for transaction in self:
            transaction.subscription_ids = tuple(
                set(transaction.sale_order_ids.mapped("subscription_ids").ids + transaction.invoice_ids.mapped("subscription_ids").ids)
            )

    @api.depends("state")
    def _compute_renewal_state(self):
        """Compute renewal state based on the transaction state."""
        for transaction in self:
            if transaction.state in ["draft", "pending"]:
                renewal_state = transaction.state
            elif transaction.state in ("done", "authorized"):
                renewal_state = "authorized"
            else:
                renewal_state = "cancel"
            transaction.renewal_state = renewal_state

    ####################
    # Business Methods #
    ####################
    def _get_mandate_values(self):
        """Override to inject subscription-specific data into the mandate values."""
        mandate_values = super()._get_mandate_values()
        if self.subscription_ids and len(self.subscription_ids) == 1:
            subscription = self.subscription_ids
            start_date = subscription.start_date or fields.Date.today() - timedelta(days=1)
            start_datetime = max(
                datetime.combine(start_date, time()),
                fields.Datetime.now() - timedelta(days=1),
            )
            end_datetime = subscription.end_date and datetime.combine(subscription.end_date, time())
            mandate_values.update(
                {
                    "amount": subscription.amount_total,
                    "MRR": subscription.recurring_monthly,
                    "start_datetime": start_datetime,
                    "end_datetime": end_datetime,
                    "recurrence_unit": subscription.plan_id.billing_period_unit,
                    "recurrence_duration": subscription.plan_id.billing_period_value,
                }
            )
            return mandate_values

    def _reconcile_after_done(self):
        """Override to force invoice creation if the transaction is done for a subscription."""
        result = super()._reconcile_after_done()
        self.filtered(lambda transaction: transaction.operation != "validation").with_context(forced_invoice=True)._create_or_link_to_invoice()
        self._post_subscription_action()
        return result

    def _create_or_link_to_invoice(self):
        """Create or link invoices for subscription transactions."""
        transactions_to_invoice = self.env["payment.transaction"]
        for transaction in self:
            if len(transaction.sale_order_ids) > 1 or transaction.invoice_ids or not transaction.sale_order_ids.is_subscription:
                continue
            elif transaction.renewal_state in ["draft", "pending", "cancel"]:
                # tx should be in an authorized renewal_state otherwise _reconcile_after_done will not be called
                # but this is a safety to prevent issue when the code is called manually
                continue
            transactions_to_invoice += transaction
            transaction._cancel_draft_invoices()

        transactions_to_invoice._invoice_sale_orders()
        transactions_to_invoice.invoice_ids.with_company(self.company_id)._post()
        if not self.env.context.get("skip_sale_auto_invoice_send"):
            transactions_to_invoice.filtered(lambda transaction: not transaction.subscription_action).invoice_ids.transaction_ids._send_invoice()

    def _get_invoiced_subscription_transaction(self):
        """Get transactions already linked to a subscription invoice."""

        def _filter_invoiced_subscription(transaction):
            transaction.ensure_one()
            if len(transaction.invoice_ids) != 1:
                return False
            return any(transaction.invoice_ids.mapped("subscription_count"))

        return self.filtered(_filter_invoiced_subscription)

    def _get_partial_payment_subscription_transaction(self):
        """Filter transactions that are only a partial payment for a subscription."""
        partial_payment_transactions = self.env["payment.transaction"]
        for transaction in self:
            order = transaction.sale_order_ids.filtered(lambda so: so.state == "sale")
            if not any(order.mapped("is_subscription")):
                continue
            elif len(order) > 1:
                # we don't support multiple order per tx. Accounting should invoice manually
                partial_payment_transactions |= transaction
            elif (
                order.currency_id.compare_amounts(
                    sum(order.transaction_ids.filtered(lambda tx: tx.renewal_state == "authorized" and not tx.invoice_ids).mapped("amount")),
                    order.amount_total,
                )
                != 0
            ):
                partial_payment_transactions |= transaction
        return partial_payment_transactions

    def _invoice_sale_orders(self):
        """Override of payment to increase next_invoice_date when needed."""
        transaction_to_invoice = self - self._get_invoiced_subscription_transaction()
        transaction_to_invoice -= self._get_partial_payment_subscription_transaction()
        return super(PaymentTransaction, transaction_to_invoice)._invoice_sale_orders()

    def _finalize_post_processing(self):
        """Override of `payment` to handle reconciliation for subscription validation transactions."""
        # Avoid post processing tx whose SO is still being processed by the invoice cron
        processable_transactions = self.filtered(lambda transaction: not any(transaction.subscription_ids.mapped("is_invoice_cron")))
        processable_transactions.filtered(
            lambda transaction: transaction.operation == "validation" and transaction.subscription_ids
        )._reconcile_after_done()
        return super(PaymentTransaction, processable_transactions)._finalize_post_processing()

    def _post_subscription_action(self):
        """Execute the subscription action once the transaction is in an acceptable state.

        This will also reopen the order and remove the payment pending state.
        Partial payment should not have a subscription_action defined and therefore should not reopen the order.
        """
        for transaction in self:
            transaction.subscription_ids.pending_transaction = False
            if not transaction.subscription_action or transaction.renewal_state != "authorized":
                continue
            if transaction.subscription_action == "assign_token":
                transaction.subscription_ids._assign_token(transaction)
            if transaction.operation == "validation":
                # validation transaction have the `assign_token` `subscription_action`
                # Once the token is assigned, we are done because we don't send emails in that case.
                continue
            transaction.subscription_ids.set_open()
            transaction.subscription_ids._send_success_mail(transaction.invoice_ids, transaction)
            if transaction.subscription_action in ["manual_send_mail", "automatic_send_mail"]:
                automatic = transaction.subscription_action == "automatic_send_mail"
                for order in transaction.subscription_ids:
                    order._subscription_post_success_payment(transaction, transaction.invoice_ids, automatic=automatic)

    def _send_invoice(self):
        """Skip sending invoices for subscription transactions that have a subscription action."""
        subscription_action_transactions = self.filtered(
            lambda transaction: (
                transaction.operation != "validation"
                and transaction.subscription_action
                and transaction.renewal_state == "authorized"
                and not transaction.is_post_processed
            )
        )
        return super(PaymentTransaction, self - subscription_action_transactions)._send_invoice()

    def _set_done(self, **kwargs):
        """Clear payment exception flag on subscriptions when transaction is done."""
        self.subscription_ids.payment_exception = False
        return super()._set_done(**kwargs)

    def _set_pending(self, **kwargs):
        """Clear payment exception flag on subscriptions when transaction is pending."""
        self.subscription_ids.payment_exception = False
        return super()._set_pending(**kwargs)

    def _set_canceled(self, state_message=None, **kwargs):
        """Handle unsuccessful transaction when transaction is canceled."""
        self._handle_unsuccessful_transaction()
        return super()._set_canceled(state_message, **kwargs)

    def _set_error(self, state_message):
        """Handle unsuccessful transaction when transaction encounters an error."""
        self._handle_unsuccessful_transaction()
        return super()._set_error(state_message)

    def _handle_unsuccessful_transaction(self):
        """Unset pending transactions for subscriptions and cancel their draft invoices."""
        for transaction in self:
            subscriptions = transaction.subscription_ids
            if subscriptions:
                subscriptions.pending_transaction = False
                transaction._cancel_draft_invoices()

    def _cancel_draft_invoices(self):
        """Cancel draft invoices attached to subscriptions."""
        self.ensure_one()
        subscriptions = self.sale_order_ids.filtered("is_subscription")
        draft_invoices = subscriptions.order_line.invoice_lines.move_id.filtered(lambda am: am.state == "draft")
        if draft_invoices:
            draft_invoices.state = "cancel"
