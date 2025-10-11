# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    # Multibanco-specific fields
    easypay_mb_entity = fields.Char(
        string="Multibanco Entity",
        help="The Multibanco entity number for payment",
        readonly=True,
    )
    easypay_mb_reference = fields.Char(
        string="Multibanco Reference",
        help="The Multibanco reference number for payment",
        readonly=True,
    )
    easypay_mb_expiry_date = fields.Datetime(
        string="Multibanco Expiry Date",
        help="The expiry date for the Multibanco reference",
        readonly=True,
    )

    # MB WAY-specific fields
    easypay_mbway_phone = fields.Char(
        string="MB WAY Phone Number",
        help="The phone number used for MB WAY payment",
    )
    easypay_mbway_alias = fields.Char(
        string="MB WAY Alias",
        help="The MB WAY alias returned by EasyPay",
        readonly=True,
    )
    easypay_mbway_status = fields.Selection(
        [
            ("pending", "Pending"),
            ("waiting", "Waiting for Approval"),
            ("approved", "Approved"),
            ("declined", "Declined"),
            ("timeout", "Timeout"),
        ],
        string="MB WAY Status",
        help="The current status of the MB WAY payment request",
        readonly=True,
    )

    def _get_specific_processing_values(self, processing_values):
        """Override to add Multibanco and MB WAY specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != "easypay":
            return res

        payment_method = self.provider_id.easypay_payment_method

        # If Multibanco payment method, extract reference details
        if payment_method == "mb":
            # Get the response from parent method
            if hasattr(self, "easypay_payment_id") and self.easypay_payment_id:
                # Fetch payment details to get Multibanco reference
                payment_details = self._easypay_get_payment_details()
                method_data = payment_details.get("method", {})

                # Extract Multibanco reference details
                if method_data.get("type") == "MB":
                    self.easypay_mb_entity = method_data.get("entity")
                    self.easypay_mb_reference = method_data.get("reference")
                    expiry = method_data.get("expiration_date")
                    if expiry:
                        self.easypay_mb_expiry_date = expiry

                    # Add Multibanco details to rendering values
                    res.update(
                        {
                            "mb_entity": self.easypay_mb_entity,
                            "mb_reference": self.easypay_mb_reference,
                            "mb_expiry_date": self.easypay_mb_expiry_date,
                            "mb_amount": self.amount,
                        }
                    )

        # If MB WAY payment method, extract phone and status
        elif payment_method == "mbw":
            if hasattr(self, "easypay_payment_id") and self.easypay_payment_id:
                # Fetch payment details to get MB WAY status
                payment_details = self._easypay_get_payment_details()
                method_data = payment_details.get("method", {})

                # Extract MB WAY details
                if method_data.get("type") == "mbw":
                    self.easypay_mbway_alias = method_data.get("alias")
                    status = method_data.get("status", "pending")
                    self.easypay_mbway_status = status

                    # Add MB WAY details to rendering values
                    res.update(
                        {
                            "mbway_phone": self.easypay_mbway_phone,
                            "mbway_alias": self.easypay_mbway_alias,
                            "mbway_status": self.easypay_mbway_status,
                            "mbway_amount": self.amount,
                        }
                    )

        return res

    def _easypay_get_payment_details(self):
        """Fetch payment details from EasyPay API.

        Note: self.ensure_one()

        :return: The payment details from EasyPay
        :rtype: dict
        """
        self.ensure_one()
        if not self.easypay_payment_id:
            return {}

        endpoint = f"/2.0/single/{self.easypay_payment_id}"
        return self.provider_id._easypay_make_request(endpoint, method="GET")
