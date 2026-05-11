# -*- coding: utf-8 -*-
"""Pre-migration for 18.0.3.2.0 — pricelist refactor.

The legacy ``solt_recurring_payment.product_pricelist_view`` exposed
``product.pricelist.product_subscription_pricing_ids`` (One2many — removed).
That view is loaded before Odoo's view-validation step, so the validation
of ``website_sale.pricelist.form`` (which inherits the same parent chain)
fails with "field does not exist on the model".

We unlink any stale view on ``product.pricelist`` that still references the
removed field. ``unlink()`` cascades the related ``ir.model.data`` row, and
Odoo's standard module-update cleanup later removes the orphan
``ir.model.fields`` records and drops the ``solt_recurring_pricing.pricelist_id``
column via ``ir.model.fields._drop_column``.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.ui.view'].search([
        ('model', '=', 'product.pricelist'),
        ('arch_db', 'ilike', 'product_subscription_pricing_ids'),
    ]).unlink()
