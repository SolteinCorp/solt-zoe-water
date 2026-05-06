/** @odoo-module **/

import {formatMonetary} from "@web/views/fields/formatters";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {registry} from "@web/core/registry";
import {Component, onWillRender, toRaw,} from "@odoo/owl";

/**
 * Subscription Period Total Field Widget
 *
 * Similar to account-tax-totals-field, this widget displays subscription totals
 * grouped by plan in a clean, hierarchical format.
 */
export class SubscriptionPeriodTotalComponent extends Component {
    static template = "solt_recurring_payment.SubscriptionPeriodTotalField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.totals = {};
        this.formatData(this.props);
        onWillRender(() => this.formatData(this.props));
    }

    /**
     * Format the data for display, similar to tax_totals
     * Creates a hierarchical structure with non-subscription info, taxes, and plan details
     */
    formatData(props) {
        let totals = props.record.data[this.props.name];
        if (!totals) {
            return;
        }

        const currencyFmtOpts = {currencyId: props.record.data.currency_id && props.record.data.currency_id[0]};

        // Format non-subscription amounts
        totals.formatted_amount_non_subscription = formatMonetary(totals.amount_non_subscription || 0, currencyFmtOpts);
        totals.formatted_amount_tax_non_subscription = formatMonetary(totals.amount_tax_non_subscription || 0, currencyFmtOpts);
        totals.formatted_amount_total_non_subscription = formatMonetary(totals.amount_total_non_subscription || 0, currencyFmtOpts);

        // Format plan details
        totals.plans.forEach(plan => {
            plan.formatted_periodic_amount = formatMonetary(plan.periodic_amount || 0, currencyFmtOpts);
            plan.formatted_periodic_tax_amount = formatMonetary(plan.periodic_tax_amount || 0, currencyFmtOpts);
            plan.formatted_period_total = formatMonetary(plan.period_total || 0, currencyFmtOpts);
            plan.formatted_price_unit = formatMonetary(plan.price_unit || 0, currencyFmtOpts);
        });

        totals.formatted_amount_subscription_subtotal = formatMonetary(totals.amount_subscription_subtotal || 0, currencyFmtOpts);
        totals.formatted_amount_subscription_tax = formatMonetary(totals.amount_subscription_tax || 0, currencyFmtOpts);
        totals.formatted_amount_subscription_total = formatMonetary(totals.amount_subscription_total || 0, currencyFmtOpts);

        this.totals = totals;
    }
}

export const subscriptionPeriodTotalComponent = {
    component: SubscriptionPeriodTotalComponent,
};

registry.category("fields").add("subscription-period-total-field", subscriptionPeriodTotalComponent);
