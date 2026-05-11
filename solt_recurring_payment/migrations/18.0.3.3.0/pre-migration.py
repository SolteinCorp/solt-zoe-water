# -*- coding: utf-8 -*-
"""Pre-migration for 18.0.3.3.0 — move prepaid flag from pricing to plan.

The ``prepaid`` Boolean used to live on ``solt.recurring.pricing`` and was
configured per-pricing alongside ``required_recurring_quantity``. It now lives
on ``solt.recurring.plan`` (one source of truth — every pricing under a plan
shares the same prepaid semantics), with ``pricing.prepaid`` becoming a
``related`` field that mirrors the plan and ``pricing.required_recurring_quantity``
auto-computed to ``plan.billing_period_value`` when prepaid.

We promote the per-pricing flag to the plan level before Odoo recomputes the
new related/stored field — which would otherwise reset every existing
``pricing.prepaid`` to False (the plan's default).

Safe on fresh DBs where the old ``solt_recurring_pricing.prepaid`` column
never existed: we check ``information_schema.columns`` first and skip the
data carry-over when nothing needs to be migrated.
"""


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return cr.fetchone() is not None


def migrate(cr, version):
    # Pre-create the prepaid column on solt_recurring_plan so we can populate
    # it BEFORE _auto_init runs. The IF NOT EXISTS makes the migration safe to
    # re-run.
    cr.execute("""
        ALTER TABLE solt_recurring_plan
        ADD COLUMN IF NOT EXISTS prepaid BOOLEAN DEFAULT FALSE
    """)
    # Carry over only if the legacy column actually exists in this DB.
    # Fresh installs and DBs that never had the old per-pricing prepaid flag
    # simply skip this step.
    if not _column_exists(cr, "solt_recurring_pricing", "prepaid"):
        return
    cr.execute("""
        UPDATE solt_recurring_plan p
        SET prepaid = TRUE,
            billing_period_value = GREATEST(
                p.billing_period_value,
                COALESCE((
                    SELECT MAX(rp.required_recurring_quantity)
                    FROM solt_recurring_pricing rp
                    WHERE rp.plan_id = p.id
                      AND rp.prepaid = TRUE
                      AND rp.required_recurring_quantity > 1
                ), 0)
            )
        WHERE EXISTS (
            SELECT 1 FROM solt_recurring_pricing rp
            WHERE rp.plan_id = p.id
              AND rp.prepaid = TRUE
              AND rp.required_recurring_quantity > 1
        )
    """)
