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

    def _iter_subscription_pricings(self, product=None):
        """Yield one pricing per active plan for this template/variant."""
        self.ensure_one()
        target = product or self
        is_template = not product and self._name == "product.template"
        seen_plans = self.env["solt.recurring.plan"]
        for pricing in self.product_subscription_pricing_ids:
            if not pricing.plan_id.active:
                continue
            if not is_template and not pricing._applies_to(target):
                continue
            if pricing.plan_id in seen_plans:
                continue
            seen_plans |= pricing.plan_id
            yield pricing

    def _website_can_be_added(self, pricelist=None, pricing=None, product=None):
        """Check if the recurring product can be added to the website cart."""
        target_product = product or self
        if not target_product.recurring_ok:
            return True
        if pricing:
            return True
        return bool(
            self.env["solt.recurring.pricing"]
            .sudo()
            ._get_first_suitable_recurring_pricing(target_product)
        )

    def _get_additionnal_combination_info(
        self, product_or_template, quantity, date, website
    ):
        """Extend combination info with subscription pricing data for the frontend.

        For each active plan, the (product, plan) list price comes from
        ``solt.recurring.pricing.price``; the website pricelist's plan-scoped
        rule is then applied on top so the standard Odoo discount/strikethrough
        rendering works the same as for non-recurring products.
        """
        combination_info = super()._get_additionnal_combination_info(
            product_or_template, quantity, date, website
        )

        if not product_or_template.recurring_ok:
            return combination_info

        currency = website.currency_id
        pricelist = website.pricelist_id
        Pricing = self.env["solt.recurring.pricing"].sudo()
        requested_plan = request and request.params.get("plan_id")
        requested_plan = requested_plan and requested_plan.isdigit() and int(requested_plan)

        real_pricings = []
        real_default_pricing = False
        product_taxes = combination_info.get("product_taxes", False)
        for pricing_record in product_or_template.sudo()._iter_subscription_pricings():
            list_price = pricing_record.price
            if pricing_record.currency_id != currency:
                list_price = pricing_record.currency_id._convert(
                    from_amount=list_price,
                    to_currency=currency,
                    company=self.env.company,
                    date=date,
                )
            unit_price = Pricing._apply_pricelist_rule(
                list_price, pricelist, product_or_template, pricing_record.plan_id,
                quantity, product_or_template.uom_id, date, currency=currency,
            )

            if product_taxes:
                list_price = self.env["product.template"]._apply_taxes_to_price(
                    list_price, currency, product_taxes,
                    combination_info["taxes"], product_or_template,
                )
                unit_price = self.env["product.template"]._apply_taxes_to_price(
                    unit_price, currency, product_taxes,
                    combination_info["taxes"], product_or_template,
                )

            # Prepaid plans: the customer pays N periods upfront. We expand
            # the displayed total so it matches what they're committing to
            # and add a ``N x per_period`` breakdown next to it.
            is_prepaid = pricing_record.prepaid and pricing_record.required_recurring_quantity > 1
            periods = pricing_record.required_recurring_quantity if is_prepaid else 1
            display_unit_price = unit_price * periods
            display_list_price = list_price * periods
            breakdown = (
                f"{periods} x {format_amount(self.env, amount=unit_price, currency=currency)}"
                if is_prepaid else ""
            )

            has_discount = currency.compare_amounts(display_unit_price, display_list_price) < 0
            formatted_unit = format_amount(self.env, amount=display_unit_price, currency=currency)
            formatted_list = format_amount(self.env, amount=display_list_price, currency=currency)
            pricing_entry = {
                "plan_id": pricing_record.plan_id.id,
                "price": f"{pricing_record.plan_id.name}: {formatted_unit}",
                "price_value": display_unit_price,
                "list_price_value": display_list_price,
                "table_price": formatted_unit,
                "table_list_price": formatted_list,
                "table_name": pricing_record.plan_id.name.replace(" ", " "),
                "has_discount": has_discount,
                "breakdown": breakdown,
                "is_prepaid": is_prepaid,
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

        no_sub_price = combination_info["price"]
        no_sub_list_price = combination_info.get("list_price", no_sub_price)
        no_sub_formatted = format_amount(self.env, amount=no_sub_price, currency=currency)
        no_sub_label = _("Single purchase")
        no_sub_entry = {
            "plan_id": 0,
            "price": f"{no_sub_label}: {no_sub_formatted}",
            "price_value": no_sub_price,
            "list_price_value": no_sub_list_price,
            "breakdown": "",
            "is_prepaid": False,
            "table_price": no_sub_formatted,
            "table_list_price": format_amount(self.env, amount=no_sub_list_price, currency=currency),
            "table_name": no_sub_label,
            "has_discount": currency.compare_amounts(no_sub_price, no_sub_list_price) < 0,
            "can_be_added": True,
            "is_no_subscription": True,
            "to_minimum_billing_period": "—",
        }
        pricings_list = [no_sub_entry] + real_pricings

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
            "list_price": default_pricing["list_price_value"],
            "has_discounted_price": default_pricing["has_discount"],
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

    def _get_sales_prices(self, website):
        """Flag subscription products without overriding the list price."""
        prices = super()._get_sales_prices(website)
        pricelist = website.pricelist_id
        fiscal_position = website.fiscal_position_id.sudo()
        currency = website.currency_id or pricelist.currency_id or self.env.company.currency_id
        today = fields.Date.context_today(self)
        Pricing = self.env["solt.recurring.pricing"].sudo()

        for template in self.filtered("recurring_ok"):
            pricing_record = Pricing._get_first_suitable_recurring_pricing(template)
            if not pricing_record:
                prices[template.id].update(
                    {
                        "is_subscription": True,
                        "is_plan_possible": False,
                    }
                )
                continue

            list_price = pricing_record.price
            if currency != pricing_record.currency_id:
                list_price = pricing_record.currency_id._convert(
                    from_amount=list_price,
                    to_currency=currency,
                    company=self.env.company,
                    date=today,
                )
            unit_price = Pricing._apply_pricelist_rule(
                list_price, pricelist, template, pricing_record.plan_id,
                1.0, template.uom_id, today, currency=currency,
            )

            product_taxes = template.sudo().taxes_id.filtered(
                lambda tax: tax.company_id == tax.env.company
            )
            if product_taxes:
                mapped_taxes = fiscal_position.sudo().map_tax(product_taxes)
                list_price = self.env["product.template"]._apply_taxes_to_price(
                    list_price, currency, product_taxes, mapped_taxes, template
                )
                unit_price = self.env["product.template"]._apply_taxes_to_price(
                    unit_price, currency, product_taxes, mapped_taxes, template
                )

            plan_record = pricing_record.plan_id
            prices[template.id].update(
                {
                    "is_subscription": True,
                    "price_reduce": unit_price,
                    "price": list_price,
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