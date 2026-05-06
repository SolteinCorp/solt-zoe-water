from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import format_amount


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.constrains("optional_product_ids")
    def _constraints_optional_product_ids(self):
        for template in self:
            if not template.recurring_ok:
                continue
            plan_ids = set(template.product_subscription_pricing_ids.plan_id.ids)
            for optional_template in template.optional_product_ids:
                if not optional_template.recurring_ok:
                    continue
                optional_plan_ids = optional_template.product_subscription_pricing_ids.plan_id.ids
                if not plan_ids.intersection(optional_plan_ids):
                    raise UserError(
                        _("You cannot have an optional product that has no common pricing plan.")
                    )

    def _get_pricelist_pricings(self, pricelist, product=None):
        """Yield available subscription pricings for this template, filtered by pricelist.

        Iterates through product_subscription_pricing_ids sorted so pricelist-specific
        pricings come first. Yields only the first pricing per plan.
        """
        self.ensure_one()
        is_template = not product and self._name == "product.template"
        seen_plans = self.env["solt.recurring.plan"]
        for pricing in self.product_subscription_pricing_ids.sorted(
            lambda pricing_rule: not pricing_rule.pricelist_id
        ):
            if not pricing.plan_id.active:
                continue
            if pricing.pricelist_id and pricing.pricelist_id != pricelist:
                continue
            if not is_template and not pricing._applies_to(product or self):
                continue
            if pricing.plan_id not in seen_plans:
                yield pricing
                seen_plans |= pricing.plan_id

    def _website_can_be_added(self, pricelist=None, pricing=None, product=None):
        """Check if the recurring product can be added to the website cart."""
        target_product = product or self
        if not target_product.recurring_ok:
            return True
        if pricing:
            return not pricing.pricelist_id or pricing.pricelist_id == pricelist
        website = self.env["website"].get_current_website()
        return bool(
            self.env["solt.recurring.pricing"]
            .sudo()
            ._get_first_suitable_recurring_pricing(
                target_product, pricelist=pricelist or website.pricelist_id
            )
        )

    def _get_additionnal_combination_info(
        self, product_or_template, quantity, date, website
    ):
        """Extend combination info with subscription pricing data for the frontend."""
        combination_info = super()._get_additionnal_combination_info(
            product_or_template, quantity, date, website
        )

        if not product_or_template.recurring_ok:
            return combination_info

        # No pricelist discount for subscription prices
        combination_info["list_price"] = combination_info["price"]
        currency = website.currency_id
        pricelist = website.pricelist_id
        requested_plan = request and request.params.get("plan_id")
        requested_plan = requested_plan and requested_plan.isdigit() and int(requested_plan)

        real_pricings = []
        real_default_pricing = False
        for pricing_record in product_or_template.sudo()._get_pricelist_pricings(pricelist):
            unit_price = pricing_record.price
            if pricing_record.currency_id != currency:
                unit_price = pricing_record.currency_id._convert(
                    from_amount=unit_price,
                    to_currency=currency,
                    company=self.env.company,
                    date=date,
                )

            product_taxes = combination_info.get("product_taxes", False)
            if product_taxes:
                unit_price = self.env["product.template"]._apply_taxes_to_price(
                    unit_price,
                    currency,
                    product_taxes,
                    combination_info["taxes"],
                    product_or_template,
                )

            formatted_price = format_amount(self.env, amount=unit_price, currency=currency)
            pricing_entry = {
                "plan_id": pricing_record.plan_id.id,
                "price": f"{pricing_record.plan_id.name}: {formatted_price}",
                "price_value": unit_price,
                "table_price": formatted_price,
                "table_name": pricing_record.plan_id.name.replace(" ", " "),
                "can_be_added": True,
                "is_no_subscription": False,
            }

            if requested_plan and (not real_default_pricing or pricing_entry["plan_id"] == requested_plan):
                real_default_pricing = pricing_entry
            real_pricings.append(pricing_entry)

        if not real_pricings:
            combination_info.update(
                {
                    "is_subscription": True,
                    "is_plan_possible": False,
                    "pricings": [],
                }
            )
            return combination_info

        # Calculate normalized prices for real plans only
        plan_ids = self.env["solt.recurring.plan"].browse(
            entry["plan_id"] for entry in real_pricings
        )
        period_to_year = {"year": 1, "month": 12, "week": 52}
        unit_translation = {"year": _("year"), "month": _("month"), "week": _("week")}
        minimum_period = min(
            plan_ids.mapped("billing_period_unit"),
            key=lambda billing_unit: 1 / period_to_year[billing_unit],
        )
        for pricing_entry in real_pricings:
            plan_record = plan_ids.browse(pricing_entry["plan_id"])
            normalized_price = (
                pricing_entry["price_value"]
                / plan_record.billing_period_value
                * period_to_year[plan_record.billing_period_unit]
                / period_to_year[minimum_period]
            )
            pricing_entry["to_minimum_billing_period"] = (
                f"{format_amount(self.env, amount=normalized_price, currency=currency)}"
                f" / {unit_translation.get(minimum_period, minimum_period)}"
            )

        # Build "Sin suscripción / Pago único" as the default first option (plan_id=0)
        no_sub_price = combination_info["price"]
        no_sub_formatted = format_amount(self.env, amount=no_sub_price, currency=currency)
        no_sub_label = _("No subscription")
        no_sub_entry = {
            "plan_id": 0,
            "price": f"{no_sub_label}: {no_sub_formatted}",
            "price_value": no_sub_price,
            "table_price": no_sub_formatted,
            "table_name": no_sub_label,
            "can_be_added": True,
            "is_no_subscription": True,
            "to_minimum_billing_period": "—",
        }
        pricings_list = [no_sub_entry] + real_pricings

        # Default: no-subscription unless a specific real plan was explicitly requested
        default_pricing = real_default_pricing if requested_plan else no_sub_entry
        default_price = default_pricing["price_value"]
        subscription_default_pricing_price = (
            format_amount(self.env, amount=default_price, currency=currency)
            if default_pricing.get("is_no_subscription")
            else default_pricing["price"]
        )

        return {
            **combination_info,
            "is_subscription": True,
            "pricings": pricings_list,
            "is_plan_possible": True,
            "price": default_price,
            "subscription_default_pricing_price": subscription_default_pricing_price,
            "subscription_default_pricing_plan_id": default_pricing["plan_id"],
            "subscription_pricing_select": True,
            "prevent_zero_price_sale": (
                website.prevent_zero_price_sale and currency.is_zero(default_price)
            ),
        }

    def _search_render_results_prices(self, mapping, combination_info):
        """Render subscription pricing for search bar results."""
        if not combination_info.get("is_subscription"):
            return super()._search_render_results_prices(mapping, combination_info)

        if not combination_info["is_plan_possible"]:
            return "", 0

        return (
            self.env["ir.ui.view"]._render_template(
                "website_solt_sale_recurring_payment.subscription_search_result_price",
                values={
                    "subscription_default_pricing_price": combination_info[
                        "subscription_default_pricing_price"
                    ],
                },
            ),
            0,
        )

    def _get_sales_prices(self, pricelist, fiscal_position):
        """Extend catalog pricing to include subscription pricing info."""
        prices = super()._get_sales_prices(pricelist, fiscal_position)
        currency = pricelist.currency_id or self.env.company.currency_id
        today = fields.Date.context_today(self)

        for template in self.filtered("recurring_ok"):
            pricing_record = (
                self.env["solt.recurring.pricing"]
                .sudo()
                ._get_first_suitable_recurring_pricing(template, pricelist=pricelist)
            )
            if not pricing_record:
                prices[template.id].update(
                    {
                        "is_subscription": True,
                        "is_plan_possible": False,
                    }
                )
                continue

            unit_price = pricing_record.price

            if currency != pricing_record.currency_id:
                unit_price = pricing_record.currency_id._convert(
                    from_amount=unit_price,
                    to_currency=currency,
                    company=self.env.company,
                    date=today,
                )

            product_taxes = template.sudo().taxes_id.filtered(
                lambda tax: tax.company_id == tax.env.company
            )
            if product_taxes:
                mapped_taxes = fiscal_position.sudo().map_tax(product_taxes)
                unit_price = self.env["product.template"]._apply_taxes_to_price(
                    unit_price, currency, product_taxes, mapped_taxes, template
                )

            plan_record = pricing_record.plan_id
            prices[template.id].update(
                {
                    "is_subscription": True,
                    "price_reduce": unit_price,
                    "is_plan_possible": template._website_can_be_added(
                        pricelist=pricelist, pricing=pricing_record
                    ),
                    "temporal_unit_display": plan_record.billing_period_display_sentence,
                }
            )
        return prices

    def _website_show_quick_add(self):
        self.ensure_one()
        return super()._website_show_quick_add() and self._website_can_be_added()

    def _can_be_added_to_cart(self):
        self.ensure_one()
        return super()._can_be_added_to_cart() and self._website_can_be_added()
