# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    easypay_payment_method = fields.Selection(
        selection=[
            ("mb", "Multibanco"),
            ("mbw", "MB Way"),
        ],
        ondelete={
            "mb": "set default",
            "mbw": "set default",
        },
    )
