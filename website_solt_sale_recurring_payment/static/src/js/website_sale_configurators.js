/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({

    /**
     * Pass subscription plan_id to product configurator dialogs.
     *
     * @override
     */
    _getAdditionalDialogProps() {
        const dialogProps = this._super(...arguments);
        if (this.rootProduct.plan_id) {
            dialogProps.subscriptionPlanId = this.rootProduct.plan_id;
        }
        return dialogProps;
    },

    /**
     * Include subscription plan_id in RPC parameters for server-side processing.
     *
     * @override
     */
    _getAdditionalRpcParams() {
        const rpcParams = this._super(...arguments);
        if (this.rootProduct.plan_id) {
            rpcParams.plan_id = this.rootProduct.plan_id;
        }
        return rpcParams;
    },
});
