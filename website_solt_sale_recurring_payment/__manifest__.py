{
    "name": "Website Sale Recurring Payments",
    "summary": "Website, Soltein, Recurring Payments, Subscriptions",
    "author": "Soltein SA de CV",
    "website": "https://soltein.mx",
    "category": "Soltein SA de CV/Sales",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "depends": [
        "website_common",
        "solt_sale_recurring_payment",
        "website_solt_recurring_payment",
        "website_sale",
    ],
    "data": [
        "templates/payment_form_templates.xml",
        "templates/subscription_templates.xml",
        "templates/sale_order.xml",
        "templates/shop_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "website_solt_sale_recurring_payment/static/src/scss/solt-sale-subscriptions.scss",
            (
                "before",
                "website_sale/static/src/js/website_sale.js",
                "website_solt_sale_recurring_payment/static/src/js/variant_mixin.js",
            ),
            "website_solt_sale_recurring_payment/static/src/js/website_sale_recurring.js",
            "website_solt_sale_recurring_payment/static/src/js/website_sale_configurators.js",
            "website_solt_sale_recurring_payment/static/src/js/payment_form.js",
            "website_solt_sale_recurring_payment/static/src/js/portal_subscription.js",
            "website_solt_sale_recurring_payment/static/src/xml/*.xml",
        ]
    },
    "installable": True,
    "application": False,
    "auto_install": True,
}
