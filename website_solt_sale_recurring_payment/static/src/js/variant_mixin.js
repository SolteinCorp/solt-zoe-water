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
        parentElement.querySelector(".js_main_product .o_subscription_plan_dropdown");
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
        // Snapshot the user's current plan selection (hidden input) before re-render
        const previousValue = pricingSelector.querySelector("input.plan_select")?.value;
        combination.formated_compared_price = pricingSelector.querySelector("del")?.textContent;
        pricingSelector.replaceWith(
            renderToElement("website_solt_sale_recurring_payment.SubscriptionPricingSelect", {
                combination_info: combination,
            })
        );

        // Restore user's plan selection if still available in new combination
        if (previousValue && combination.pricings.find(p => p.plan_id === parseInt(previousValue))) {
            const newDropdown = parentElement.querySelector(".js_main_product .o_subscription_plan_dropdown");
            if (newDropdown) {
                const newHidden = newDropdown.querySelector("input.plan_select");
                if (newHidden) {
                    newHidden.value = previousValue;
                }
                const newLabel = newDropdown.querySelector(".o_plan_select_toggle .o_plan_label");
                const newOption = newDropdown.querySelector(`.o_plan_option[data-plan-id="${previousValue}"]`);
                if (newLabel && newOption) {
                    newLabel.innerHTML = newOption.innerHTML;
                }
            }
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
