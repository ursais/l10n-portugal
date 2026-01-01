# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Payment Provider: EasyPay - Multibanco & MB WAY",
    "version": "18.0.1.0.0",
    "category": "Accounting/Payment Providers",
    "summary": "Add Multibanco and MB WAY payment providers to EasyPay",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-portugal",
    "license": "LGPL-3",
    "depends": ["payment_easypay", "l10n_pt_payment"],
    "data": [
        "data/payment_provider_data.xml",
        "views/payment_easypay_mb_templates.xml",
    ],
    "demo": [
        "demo/payment_provider_demo.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "payment_easypay_mb/static/src/scss/multibanco.scss",
        ],
    },
    "installable": True,
    "auto_install": True,
}
