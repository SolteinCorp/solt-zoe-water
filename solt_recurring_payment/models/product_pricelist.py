# -*- coding: utf-8 -*-
from odoo import models
from odoo.osv import expression


class Pricelist(models.Model):
    _inherit = "product.pricelist"

    def _get_applicable_rules_domain(self, products, date, **kwargs):
        """Filter pricelist items by ``plan_id`` from context.

        Three modes via context:
        - ``plan_id=X`` + ``plan_strict=True`` → only rules targeting plan X.
        - ``plan_id=X`` (no plan_strict) → only plan-agnostic rules
          (``plan_id=False``). Combined with the two-pass logic in
          ``solt.recurring.pricing._apply_pricelist_rule`` (strict first,
          agnostic fallback), this guarantees plan-specific rules win over
          plan-agnostic ones when both match.
        - no plan_id → non-recurring line: only plan-agnostic rules.
        """
        domain = super()._get_applicable_rules_domain(products, date, **kwargs)
        plan_id = self.env.context.get('plan_id')
        if plan_id and self.env.context.get('plan_strict'):
            domain = expression.AND([domain, [('plan_id', '=', plan_id)]])
        else:
            domain = expression.AND([domain, [('plan_id', '=', False)]])
        return domain
