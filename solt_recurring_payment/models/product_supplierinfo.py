# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    recurring_ok = fields.Boolean(related='product_tmpl_id.recurring_ok', string='Recurring OK', readonly=True,
                                  help='Indicates whether the product can be sold or bought recurringly. This field is inherited from the product template and cannot be edited directly on the supplier info. To change this setting, please edit the product template.')
    plan_id = fields.Many2one(comodel_name='solt.recurring.plan', string='Plan de Suscripción', ondelete='set null',
                              help="Cuando se establece, este precio aplica únicamente a suscripciones que usen este plan recurrente. Dejar vacío para que aplique independientemente del plan.", )
    required_recurring_quantity = fields.Integer(string='Periodos Requeridos', default=0,
                                                 help="Número mínimo de periodos de suscripción requeridos para este precio de proveedor.", )
    prepaid = fields.Boolean(
        string='Prepaid',
        default=False,
        help="When enabled, the first vendor bill charges the full prepaid amount of the "
             "required periods upfront and is recorded as an advance to the supplier. "
             "Each subsequent monthly bill is automatically settled from that advance "
             "until exhausted.",
    )

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
            self.prepaid = False
        else:
            self.recurring_ok = self.product_tmpl_id.recurring_ok

    def _get_filtered_supplier(self, company_id, product_id, params):
        res = super()._get_filtered_supplier(company_id, product_id, params)
        plan = params.get('plan_id') if params else None
        if res and plan and product_id and product_id.recurring_ok:
            return res.filtered(lambda s: not s.plan_id or s.plan_id == plan)
        return res
