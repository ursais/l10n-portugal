# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from .. import const

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    easypay_payment_id = fields.Char(
        string="EasyPay Payment ID",
        help="The payment ID returned by EasyPay",
        readonly=True,
    )
    easypay_transaction_id = fields.Char(
        string="EasyPay Transaction ID",
        help="The transaction ID returned by EasyPay",
        readonly=True,
    )
    easypay_checkout_id = fields.Char(
        string="EasyPay Checkout ID",
        help="The checkout session ID returned by EasyPay",
        readonly=True,
    )
    easypay_payment_url = fields.Char(
        string="EasyPay Payment URL",
        help="The URL to redirect the customer to complete payment",
        readonly=True,
    )
    token_id = fields.Many2one(
        string="Payment Token",
        comodel_name="payment.token",
        readonly=True,
        domain='[("provider_id", "=", "provider_id")]',
        ondelete="restrict",
        help="The payment token for frequent payments (tokenization)",
    )

    def _get_specific_processing_values(self, processing_values):
        """Override of payment to return EasyPay-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != "easypay":
            return res

        if self.provider_id.easypay_use_checkout:
            # Checkout flow - SDK-based inline payment
            # Don't create session yet - wait until user actually pays
            res.update(
                {
                    "easypay_use_checkout": True,
                    "api_url": self.provider_id._easypay_get_api_url(),
                }
            )
        else:
            # Single Payment flow - redirect to hosted page
            response = self.provider_id._easypay_create_single_payment(self.sudo())
            self.easypay_payment_id = response.get("id")
            payment_url = response.get("method", {}).get("url")
            res.update(
                {
                    "easypay_payment_id": self.easypay_payment_id,
                    "easypay_payment_url": payment_url,
                }
            )
        return res

    def _get_specific_rendering_values(self, processing_values):
        """Override of payment to return EasyPay-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values
        :return: The dict of provider-specific rendering values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "easypay":
            return res

        if self.provider_id.easypay_use_checkout:
            # Checkout flow - pass SDK data
            res.update(
                {
                    "checkout_manifest": processing_values.get("checkout_manifest"),
                    "checkout_id": processing_values.get("checkout_id"),
                    "api_url": processing_values.get("api_url"),
                }
            )
        else:
            # Single Payment flow - pass redirect URL
            res.update(
                {
                    "easypay_payment_url": processing_values.get("easypay_payment_url"),
                }
            )
        return res

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Override of payment to find the transaction based on EasyPay data.

        :param str provider_code: The provider code
        :param dict notification_data: The notification data
        :return: The transaction
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If the transaction is not found
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != "easypay" or len(tx) == 1:
            return tx

        # Try to find transaction by reference or EasyPay IDs
        reference = notification_data.get("key")
        payment_id = notification_data.get("id")

        if reference:
            tx = self.search(
                [("reference", "=", reference), ("provider_code", "=", "easypay")]
            )
        elif payment_id:
            tx = self.search(
                [
                    "|",
                    ("easypay_payment_id", "=", payment_id),
                    ("easypay_checkout_id", "=", payment_id),
                    ("provider_code", "=", "easypay"),
                ]
            )

        if not tx:
            raise ValidationError(
                _(
                    "EasyPay: No transaction found matching reference %s.",
                    reference,
                )
            )
        return tx

    def _process_notification_data(self, notification_data):
        """Override of payment to process the notification data."""
        super()._process_notification_data(notification_data)
        if self.provider_code != "easypay":
            return

        # Extract relevant data from notification
        payment_id = notification_data.get("id")
        # EasyPay API uses 'payment_status' for Single Payment
        # and 'status' for other flows
        status = notification_data.get("payment_status") or notification_data.get(
            "status"
        )

        # Update transaction with EasyPay data
        if payment_id and not self.easypay_payment_id:
            self.easypay_payment_id = payment_id

        # Map 'paid' status to 'success' for consistency
        if status == "paid":
            status = "success"

        # Update the payment state
        payment_state = next(
            (
                state
                for state, easypay_statuses in const.STATUS_MAPPING.items()
                if status in easypay_statuses
            ),
            None,
        )

        if payment_state == "pending":
            self._set_pending()
        elif payment_state == "authorized":
            self._set_authorized()
        elif payment_state == "done":
            self._set_done()
        elif payment_state == "cancel":
            self._set_canceled()
        elif payment_state == "error":
            error_msg = notification_data.get("messages", ["Payment failed"])
            if isinstance(error_msg, list):
                error_msg = ", ".join(error_msg)
            self._set_error(error_msg)
        else:
            _logger.warning(
                "received notification for transaction with reference %s "
                "with unknown status: %s",
                self.reference,
                status,
            )

    def _easypay_get_payment_details(self):
        """Fetch payment details from EasyPay API.

        Note: self.ensure_one()

        :return: The payment details
        :rtype: dict
        :raise ValidationError: If no payment ID is found
        """
        self.ensure_one()

        if not self.easypay_payment_id:
            raise ValidationError(_("No EasyPay payment ID found for this transaction"))

        endpoint = f"/2.0/single/{self.easypay_payment_id}"
        return self.provider_id._easypay_make_request(endpoint, method="GET")

    def _send_refund_request(self, amount_to_refund=None):
        """Send refund request to EasyPay."""
        if self.provider_code != "easypay":
            return super()._send_refund_request(amount_to_refund=amount_to_refund)

        if not self.easypay_transaction_id:
            payment_details = self._easypay_get_payment_details()
            self.easypay_transaction_id = payment_details.get("capture", {}).get("id")

        refund_amount = amount_to_refund or self.amount
        response = self.provider_id._easypay_make_request(
            f"/2.0/capture/{self.easypay_transaction_id}/refund",
            {"transaction_id": self.easypay_transaction_id, "value": refund_amount},
        )

        refund_tx = self._create_refund_transaction(amount_to_refund=refund_amount)
        refund_tx.easypay_payment_id = response.get("id")
        return refund_tx

    def _send_capture_request(self):
        """Send capture request to EasyPay."""
        if self.provider_code != "easypay":
            return super()._send_capture_request()

        if self.easypay_payment_id:
            endpoint = f"/2.0/single/{self.easypay_payment_id}/capture"
            payload = {
                "transaction_key": self.reference,
                "value": self.amount,
            }
        elif self.easypay_transaction_id:
            endpoint = "/2.0/capture"
            payload = {
                "transaction_id": self.easypay_transaction_id,
                "transaction_key": self.reference,
                "value": self.amount,
            }
        else:
            raise ValidationError(
                _("Cannot capture: No EasyPay payment ID or token found")
            )

        response = self.provider_id._easypay_make_request(endpoint, payload)
        self.easypay_transaction_id = response.get("id")
        self._set_done()

    def _send_void_request(self):
        """Send void request to EasyPay."""
        if self.provider_code != "easypay":
            return super()._send_void_request()

        self.provider_id._easypay_make_request(
            f"/2.0/authorisation/{self.easypay_payment_id}/void", {}
        )
        self._set_canceled()
