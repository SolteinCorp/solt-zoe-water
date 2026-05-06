# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    recurring_ok = fields.Boolean(
        'Is Recurring',
        help='Indicates whether this product can be sold or buy recurringly.',
    )

    product_subscription_pricing_ids = fields.One2many(
        'solt.recurring.pricing',
        'product_template_id',
        string="Custom Subscription Pricings",
        help="Custom subscription pricing rules for this product. Only users with sales access can manage these rules.",
        auto_join=True,
        copy=False
    )

    @api.model
    def _get_incompatible_types(self):
        return ['recurring_ok'] + super()._get_incompatible_types()

    def copy(self, default=None):
        """Override copy to duplicate subscription pricing rules along with the product.

        When copying a product template with subscription pricing, this method ensures that
        all pricing rules are also copied to the new template, maintaining the relationship
        with the correct product variants.

        Args:
            default: Dictionary of default values to override in the copy.

        Returns:
            product.template: The newly created product template record.

        Raises:
            UserError: If user doesn't have sales application access when copying
                      a product with subscription pricing.
        """
        copied_tmpl = super().copy(default)
        if not self.sudo().product_subscription_pricing_ids:
            return copied_tmpl
        for pricing in self.product_subscription_pricing_ids:
            copied_variant_ids = []
            for product in pricing.product_variant_ids:
                pav_ids = tuple(product.product_template_variant_value_ids.product_attribute_value_id.ids)
                copied_variant_ids.extend(
                    copied_tmpl.product_variant_ids.filtered(
                        lambda p, pav=pav_ids: tuple(
                            p.product_template_variant_value_ids.product_attribute_value_id.ids) == pav
                    ).ids
                )
            pricing.copy({
                'product_template_id': copied_tmpl.id,
                'product_variant_ids': copied_variant_ids,
            })
        return copied_tmpl
