from odoo.addons.website_sale.controllers import main as website_sale_portal
from odoo.addons.website_sale.controllers.variant import WebsiteSaleVariantController
from odoo.http import route


class WebsiteSaleRecurringVariantController(WebsiteSaleVariantController):
    @route()
    def get_combination_info_website(self, *args, **kwargs):
        """Enforce both variant and plan availability on combination info."""
        combination_response = super().get_combination_info_website(*args, **kwargs)
        is_combination_valid = combination_response.get("is_combination_possible", True)
        is_plan_valid = combination_response.get("is_plan_possible", True)
        combination_response["is_combination_possible"] = is_combination_valid and is_plan_valid
        return combination_response


class WebsiteSale(website_sale_portal.WebsiteSale):
    def _get_shop_payment_values(self, order, **kwargs):
        """Add is_subscription flag to payment values for subscription orders."""
        payment_values = super()._get_shop_payment_values(order, **kwargs)
        payment_values["is_subscription"] = order.is_subscription
        return payment_values
