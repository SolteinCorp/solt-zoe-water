# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    recurring_ok = fields.Boolean(related='product_tmpl_id.recurring_ok', string='Recurring OK', readonly=True,
                                  help='Indicates whether the product can be sold or bought recurringly. This field is inherited from the product template and cannot be edited directly on the supplier info. To change this setting, please edit the product template.')
    plan_id = fields.Many2one(
        comodel_name='solt.recurring.plan',
        string='Subscription Plan',
        ondelete='set null',
        help="When set, this price applies only to subscriptions using this recurring plan. Leave empty to apply regardless of the plan.",
    )
    required_recurring_quantity = fields.Integer(
        string='Required Periods',
        compute='_compute_required_recurring_quantity',
        store=True,
        readonly=False,
        precompute=True,
        help="Minimum number of recurring periods required for this vendor price. "
             "When the plan is prepaid, this is auto-set to the plan's billing_period_value "
             "and locked (the prepaid commitment covers the full plan period).",
    )
    prepaid = fields.Boolean(
        related='plan_id.prepaid',
        store=True,
        readonly=True,
        help="True when the linked plan is configured as prepaid. The prepaid flag lives on "
             "``solt.recurring.plan`` so every supplier info on the same plan shares the same "
             "prepaid semantics.",
    )

    @api.depends('plan_id', 'plan_id.prepaid', 'plan_id.billing_period_value')
    def _compute_required_recurring_quantity(self):
        for supplier in self:
            if supplier.plan_id.prepaid:
                supplier.required_recurring_quantity = supplier.plan_id.billing_period_value
            else:
                supplier.required_recurring_quantity = supplier.required_recurring_quantity or 0

    @api.constrains('prepaid', 'required_recurring_quantity')
    def _check_prepaid_required_quantity(self):
        """Prepaid supplier prices require required_recurring_quantity > 1."""
        for supplier in self:
            if supplier.prepaid and supplier.required_recurring_quantity <= 1:
                raise UserError(_(
                    "Prepaid pricing requires 'Required Periods' to be greater than 1. "
                    "If only one period is required, the price is not prepaid."
                ))

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):  # pylint: disable=W8110
        super()._onchange_product_tmpl_id()
        if not self.product_tmpl_id or not self.product_tmpl_id.recurring_ok:
            self.plan_id = False
            self.required_recurring_quantity = 0
        else:
            self.recurring_ok = self.product_tmpl_id.recurring_ok

    def _get_filtered_supplier(self, company_id, product_id, params):
        res = super()._get_filtered_supplier(company_id, product_id, params)
        plan = params.get('plan_id') if params else None
        if res and plan and product_id and product_id.recurring_ok:
            return res.filtered(lambda s: not s.plan_id or s.plan_id == plan)
        return res
