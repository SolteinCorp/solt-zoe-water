# -*- coding: utf-8 -*-
{
    "name": "Sale Recurring Payments",
    "summary": "Manage recurring revenues with subscriptions.",
    "author": "Soltein SA de CV",
    "website": "https://soltein.mx",
    "category": "Soltein SA de CV/Sales",
    "version": "18.0.3.1.0",
    "license": "LGPL-3",
    "depends": ["solt_recurring_payment", "sale_management", "payment"],
    "data": [
        "views/sale_order.xml",
        "views/solt_subscription.xml",
        "templates/sale_order.xml",
        "report/sale_report_templates.xml",
        "views/menus.xml",
    ],
    "application": True,
}
