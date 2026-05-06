/** @odoo-module **/

import VariantMixin from "@website_sale/js/sale_variant_mixin";
import { renderToElement } from "@web/core/utils/render";


/**
 * Update the subscription pricing display when the product combination changes.
 *
 * @param {Event} ev
 * @param {$.Element} $parent
 * @param {object} combination
 */
VariantMixin._onChangeCombinationSubscription = function (ev, $parent, combination) {
    if (!this.isWebsite || !combination.is_subscription) {
        return;
    }
    const parentElement = $parent.get(0);
    const subscriptionUnit = parentElement.querySelector(".o_subscription_unit");
    const subscriptionPrice = parentElement.querySelector(".o_subscription_price") || parentElement.querySelector(".product_price h5");
    const pricingSelector =
        parentElement.querySelector(".js_main_product h5:has(.o_subscription_price)") ||
        parentElement.querySelector(".js_main_product select.plan_select");
    const pricingTable = document.querySelector("#oe_wsale_subscription_pricing_table");
    const addToCartButton = document.querySelector('#add_to_cart');
    if (addToCartButton) {
        addToCartButton.dataset.subscriptionPlanId = combination.pricings.length > 0 ? combination.subscription_default_pricing_plan_id : '';
    }
    if (subscriptionUnit) {
        subscriptionUnit.textContent = combination.temporal_unit_display;
    }
    if (subscriptionPrice) {
        subscriptionPrice.textContent = combination.subscription_default_pricing_price;
    }
    if (pricingSelector) {
        combination.formated_compared_price = pricingSelector.querySelector("del")?.textContent;
        pricingSelector.replaceWith(
            renderToElement("website_solt_sale_recurring_payment.SubscriptionPricingSelect", {
                combination_info: combination,
            })
        );

        // Restore user's plan selection if still available in new combination
        if (combination.pricings.find(planPricing => planPricing.plan_id === parseInt(pricingSelector.value))) {
            const newPricingSelector = parentElement.querySelector(".js_main_product h5:has(.o_subscription_price)") ||
                parentElement.querySelector(".js_main_product select.plan_select");
            newPricingSelector.value = pricingSelector.value;
        }
    } else {
        // No pricing element exists yet — append one for the first time
        const containerNode = parentElement.querySelector(".js_main_product div div");
        containerNode.append(
            renderToElement("website_solt_sale_recurring_payment.SubscriptionPricingSelect", {
                combination_info: combination,
            })
        );
    }
    if (pricingTable) {
        pricingTable.replaceWith(
            renderToElement("website_solt_sale_recurring_payment.SubscriptionPricingTable", {
                combination_info: combination,
            })
        );
    } else {
        // No pricing table exists yet — append one after the product form
        const formNode = document.querySelector("#product_details form");
        formNode.after(
            renderToElement("website_solt_sale_recurring_payment.SubscriptionPricingTable", {
                combination_info: combination,
            })
        );
    }
};

const originalGetOptionalCombinationInfoParam = VariantMixin._getOptionalCombinationInfoParam;
/**
 * Include the selected subscription plan in combination info parameters.
 *
 * @param {$.Element} $product
 */
VariantMixin._getOptionalCombinationInfoParam = function ($product) {
    const combinationParams = originalGetOptionalCombinationInfoParam.apply(this, arguments);
    Object.assign(combinationParams, {
        'plan_id': $product?.find('.product_price .plan_select').val()
    });

    return combinationParams;
};

export default VariantMixin;
