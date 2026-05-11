/** @odoo-module **/

import VariantMixin from "@website_sale/js/sale_variant_mixin";
import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({

    /**
     * Capture the selected subscription plan and assign it to rootProduct.
     *
     * @override
     */
    _updateRootProduct($form, productId, productTemplateId) {
        this._super(...arguments);
        const selectedPlan = $form.find('.product_price .plan_select').val()
            ?? $form.find('#add_to_cart').attr('data-subscription-plan-id');
        if (selectedPlan) {
            Object.assign(this.rootProduct, {
                plan_id: parseInt(selectedPlan),
            });
        }
    },

    /**
     * Update subscription pricing display when the variant combination changes.
     *
     * @override
     */
    _onChangeCombination: function () {
        this._super.apply(this, arguments);
        VariantMixin._onChangeCombinationSubscription.apply(this, arguments);
    },
});


// Delegated click handler for the custom dropdown options — updates the
// hidden ``plan_select`` input + the visible button label so HTML survives
// (strikethrough, badge, etc). Using document-level delegation so it keeps
// working after the dropdown is re-rendered on variant change.
document.addEventListener("click", function (ev) {
    const optionEl = ev.target.closest(".o_plan_option");
    if (!optionEl) {
        return;
    }
    const dropdown = optionEl.closest(".o_subscription_plan_dropdown");
    if (!dropdown) {
        return;
    }
    const planId = optionEl.dataset.planId;
    const hidden = dropdown.querySelector("input.plan_select");
    if (hidden) {
        hidden.value = planId;
        hidden.dispatchEvent(new Event("change", { bubbles: true }));
    }
    const label = dropdown.querySelector(".o_plan_select_toggle .o_plan_label");
    if (label) {
        label.innerHTML = optionEl.innerHTML;
    }
});
