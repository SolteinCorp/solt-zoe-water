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
     * Disable non-selected plan options during the add-to-cart process
     * to prevent accidental changes.
     *
     * @override
     */
    _handleAdd($form) {
        $form.find('.plan_select > option').each(function() {
            this.disabled = !this.selected;
        });
        return this._super(...arguments);
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
