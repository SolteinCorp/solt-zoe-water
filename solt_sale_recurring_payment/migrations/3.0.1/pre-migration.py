# -*- coding: utf-8 -*-
# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Pre-migration: remove obsolete res_config_settings view and its children."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    views_with_field = env.ref('solt_sale_recurring_payment.res_config_settings_view_form', raise_if_not_found=False)
    if not views_with_field:
        return
    views_with_field.inherit_children_ids.inherit_children_ids.unlink()
    views_with_field.inherit_children_ids.unlink()
    views_with_field.unlink()
