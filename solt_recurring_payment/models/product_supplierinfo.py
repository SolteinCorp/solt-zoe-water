# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    recurring_ok = fields.Boolean(related='product_tmpl_id.recurring_ok', string='Recurring OK', readonly=True,
                                  help='Indicates whether the product can be sold or bought recurringly. This field is inherited from the product template and cannot be edited directly on the supplier info. To change this setting, please edit the product template.')
    plan_id = fields.Many2one(comodel_name='solt.recurring.plan', string='Plan de Suscripción', ondelete='set null',
                              help="Cuando se establece, este precio aplica únicamente a suscripciones que usen este plan recurrente. Dejar vacío para que aplique independientemente del plan.", )
    required_recurring_quantity = fields.Integer(string='Periodos Requeridos', default=0,
                                                 help="Número mínimo de periodos de suscripción requeridos para este precio de proveedor.", )

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
