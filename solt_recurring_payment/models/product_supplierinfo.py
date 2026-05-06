# -*- coding: utf-8 -*-
# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import api, fields, models


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    recurring_ok = fields.Boolean(
        related='product_tmpl_id.recurring_ok',
        string='Recurring OK',
        readonly=True,
        help='Indicates whether the product can be bought recurringly. '
             'Inherited from the product template; edit the template to change this.',
    )
    plan_id = fields.Many2one(
        comodel_name='solt.recurring.plan',
        string='Subscription Plan',
        ondelete='set null',
        help='When set, this price applies only to purchase subscriptions using this recurring plan. '
             'Leave empty to apply regardless of plan.',
    )
    required_recurring_quantity = fields.Integer(
        string='Required Periods',
        default=0,
        help='Minimum number of subscription periods required for this vendor price.',
    )

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):  # pylint: disable=W8110
        """Reset plan and recurring quantity when switching to a non-recurring product."""
        super()._onchange_product_tmpl_id()
        if not self.product_tmpl_id or not self.product_tmpl_id.recurring_ok:
            self.plan_id = False
            self.required_recurring_quantity = 0
        else:
            self.recurring_ok = self.product_tmpl_id.recurring_ok

    def _get_filtered_supplier(self, company_id, product_id, params):
        """Filter suppliers by plan when the product is recurring and a plan is provided."""
        result = super()._get_filtered_supplier(company_id, product_id, params)
        plan = params.get('plan_id') if params else None
        if result and plan and product_id and product_id.recurring_ok:
            return result.filtered(lambda supplier: not supplier.plan_id or supplier.plan_id == plan)
        return result
