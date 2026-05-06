# -*- coding: utf-8 -*-
from psycopg2 import sql

from . import models
from . import wizard


def pre_init_hook(env):
    """Rename tables removing 'sale_' from table names."""
    cr = env.cr

    # List of tables to rename: (old_name, new_name)
    table_renames = [
        ('solt_sale_recurring_plan', 'solt_recurring_plan'),
        ('solt_sale_recurring_plan_related_plan', 'solt_recurring_plan_related_plan'),
        ('solt_sale_recurring_pricing', 'solt_recurring_pricing'),
        ('solt_sale_subscription', 'solt_subscription'),
        ('solt_sale_subscription_close_reason', 'solt_subscription_close_reason'),
        ('solt_sale_subscription_close_wizard', 'solt_subscription_close_wizard'),
        ('solt_sale_subscription_line', 'solt_subscription_line'),
        ('solt_sale_subscription_renew_wizard', 'solt_subscription_renew_wizard'),
    ]

    for old_table, new_table in table_renames:
        # Check if old table exists
        cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """, (old_table,))

        if cr.fetchone()[0]:
            # Rename the table using psycopg2.sql for safe identifier handling
            try:
                cr.execute(
                    sql.SQL('ALTER TABLE {} RENAME TO {}').format(
                        sql.Identifier(old_table),
                        sql.Identifier(new_table)
                    )
                )
                env.cr.commit()
            except Exception as e:
                env.cr.rollback()
                raise Exception(f"Failed to rename table {old_table} to {new_table}: {str(e)}")
