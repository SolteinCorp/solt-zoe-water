from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _cart_find_product_line(self, product_id, line_id=None, **kwargs):
        """Match cart lines by (product, plan) so the same product with different plans stays on separate lines."""
        lines = super()._cart_find_product_line(product_id, line_id=line_id, **kwargs)
        if not lines or line_id:
            return lines
        product = self.env["product.product"].browse(product_id)
        if not product.recurring_ok:
            return lines
        plan_id = kwargs.get("plan_id") or 0
        plan_id = int(plan_id)
        return lines.filtered(lambda sol: (sol.plan_id.id or 0) == plan_id)

    def _cart_update_order_line(self, product_id, quantity, order_line, **kwargs):
        """Set the subscription plan on the order line when adding a recurring product.

        plan_id=0 is the "Sin suscripción / Pago único" sentinel — no subscription is created.
        For existing lines, update plan_id if a real plan is provided.
        """
        line_product_id = order_line.product_id.id if order_line else product_id
        cart_product = self.env["product.product"].browse(line_product_id)

        plan = False
        if cart_product.recurring_ok and quantity > 0:
            selected_plan_id = kwargs.get("plan_id")
            # plan_id=0 is the "Sin suscripción / Pago único" sentinel — no subscription created
            if selected_plan_id and int(selected_plan_id) != 0:
                plan = self.env["solt.recurring.plan"].browse(int(selected_plan_id))

            if plan and plan.exists():
                kwargs["plan_id"] = plan.id
            else:
                kwargs.pop("plan_id", None)

        order_line = super()._cart_update_order_line(
            product_id, quantity, order_line, **kwargs
        )

        if plan and order_line and order_line.exists() and quantity > 0:
            Pricing = self.env["solt.recurring.pricing"].sudo()
            pricing = Pricing._get_first_suitable_recurring_pricing(cart_product, plan)
            if pricing:
                base_price = pricing.currency_id._convert(
                    pricing.price,
                    order_line.currency_id,
                    order_line.company_id,
                    fields.Date.today(),
                )
                final_price = Pricing._apply_pricelist_rule(
                    base_price, self.pricelist_id, cart_product, plan,
                    order_line.product_uom_qty or 1.0, order_line.product_uom,
                    fields.Date.today(), currency=order_line.currency_id,
                )
                order_line.write({
                    'plan_id': plan.id,
                    'price_unit': final_price,
                    'required_recurring_quantity': pricing.required_recurring_quantity,
                })

        return order_line

    def _prepare_order_line_values(
        self, product_id, quantity, linked_line_id=False,
        no_variant_attribute_value_ids=None, product_custom_attribute_values=None,
        **kwargs
    ):
        """Include plan_id in the order line creation values."""
        values = super()._prepare_order_line_values(
            product_id, quantity,
            linked_line_id=linked_line_id,
            no_variant_attribute_value_ids=no_variant_attribute_value_ids,
            product_custom_attribute_values=product_custom_attribute_values,
            **kwargs,
        )
        plan_id = kwargs.get("plan_id")
        if plan_id:
            values["plan_id"] = int(plan_id)
        return values
