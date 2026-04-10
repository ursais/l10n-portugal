# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json
import logging

import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class EasyPayController(http.Controller):
    """Controller to handle EasyPay webhooks and redirects."""

    _return_url = "/payment/easypay/return"
    _generic_webhook_url = "/payment/easypay/webhook/generic"
    _authorisation_webhook_url = "/payment/easypay/webhook/authorisation"
    _transaction_webhook_url = "/payment/easypay/webhook/transaction"

    def _redirect_to_payment_status(self):
        """Standard redirect to payment status page."""
        return werkzeug.utils.redirect("/payment/status", code=303)

    def _extract_reference(self, data):
        """Extract transaction reference from data dict or URL args."""
        return (
            data.get("key")
            or data.get("reference")
            or request.httprequest.args.get("key")
            or request.httprequest.args.get("reference")
        )

    @http.route(
        _return_url,
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
        save_session=False,
    )
    def easypay_return_from_redirect(self, **data):
        """Process the return from EasyPay after payment."""
        # Parse JSON body if POST
        if (
            request.httprequest.method == "POST"
            and request.httprequest.content_type == "application/json"
        ):
            try:
                data = json.loads(request.httprequest.data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                _logger.warning("Failed to parse JSON body in return handler")
                data = {}

        reference = self._extract_reference(data)
        if reference:
            tx_sudo = self._find_transaction(None, reference)
            if tx_sudo:
                payment_id = data.get("id") or tx_sudo.easypay_payment_id
                if payment_id:
                    try:
                        payment_data = tx_sudo.provider_id._easypay_make_request(
                            f"/2.0/single/{payment_id}", method="GET"
                        )
                    except Exception as e:
                        _logger.exception(
                            "Error fetching payment data for return %s: %s",
                            reference,
                            e,
                        )
                        return self._redirect_to_payment_status()
                    try:
                        tx_sudo._handle_notification_data("easypay", payment_data)
                    except Exception as e:
                        _logger.exception(
                            "Error processing notification for return %s: %s",
                            reference,
                            e,
                        )

        return self._redirect_to_payment_status()

    @http.route(
        _generic_webhook_url,
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def _generic_webhook(self, **data):
        """Handle generic webhook from EasyPay."""
        return self._process_webhook_notification(data, "generic")

    @http.route(
        _authorisation_webhook_url,
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def _authorisation_webhook(self, **data):
        """Handle authorisation webhook from EasyPay."""
        return self._process_webhook_notification(data, "authorisation")

    @http.route(
        _transaction_webhook_url,
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def easypay_transaction_webhook(self, **data):
        """Process transaction webhook notifications from EasyPay."""
        return self._process_webhook_notification(data, "transaction")

    def _get_webhook_endpoint(self, tx_sudo, webhook_type, payment_id):
        """Return the API endpoint to fetch full payment data for a webhook.

        :param tx_sudo: The payment transaction record
        :param str webhook_type: Webhook route type ('generic', 'authorisation',
                                 'transaction')
        :param str payment_id: EasyPay payment ID from the notification body
        :return: Endpoint path or None if lookup is not possible
        :rtype: str|None
        """
        if tx_sudo.easypay_checkout_id:
            return f"/2.0/checkout/{tx_sudo.easypay_checkout_id}"
        if webhook_type == "authorisation" and payment_id:
            return f"/2.0/authorisation/{payment_id}"
        if payment_id:
            return f"/2.0/single/{payment_id}"
        return None

    def _process_webhook_notification(self, data, webhook_type):
        payment_id = data.get("id")
        reference = data.get("key")

        tx_sudo = self._find_transaction(payment_id, reference)
        if not tx_sudo:
            return request.make_json_response({}, status=200)

        endpoint = self._get_webhook_endpoint(tx_sudo, webhook_type, payment_id)
        if not endpoint:
            return request.make_json_response({}, status=200)

        try:
            payment_data = tx_sudo.provider_id._easypay_make_request(
                endpoint, method="GET"
            )
        except Exception as e:
            _logger.exception(
                "Error fetching payment data for webhook (%s): %s", webhook_type, e
            )
            return request.make_json_response({}, status=200)

        if tx_sudo.provider_id._easypay_is_frequent(payment_data):
            token_ref = payment_data.get("payment", {}).get("id") or payment_id
            tx_sudo._easypay_create_token(token_ref)

        try:
            tx_sudo._handle_notification_data("easypay", payment_data)
        except Exception as e:
            _logger.exception(
                "Error processing notification data for webhook (%s): %s",
                webhook_type,
                e,
            )

        return request.make_json_response({}, status=200)

    def _find_transaction(self, payment_id, reference):
        """Find transaction by reference or payment ID."""
        tx_sudo = request.env["payment.transaction"].sudo()
        if reference:
            return tx_sudo.search(
                [("reference", "=", reference), ("provider_code", "=", "easypay")],
                limit=1,
            )
        elif payment_id:
            return tx_sudo.search(
                [
                    "&",
                    "|",
                    ("easypay_payment_id", "=", payment_id),
                    ("easypay_checkout_id", "=", payment_id),
                    ("provider_code", "=", "easypay"),
                ],
                limit=1,
            )
        return None

    @http.route(
        "/payment/easypay/checkout/success",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
    )
    def easypay_checkout_success(self, **data):
        checkout_id = data.get("id")
        reference = data.get("key") or data.get("reference")

        if not checkout_id and not reference:
            return self._redirect_to_payment_status()

        tx_sudo = self._find_transaction(checkout_id, reference)
        if not tx_sudo:
            return self._redirect_to_payment_status()

        try:
            payment_data = tx_sudo.provider_id._easypay_make_request(
                f"/2.0/checkout/{tx_sudo.easypay_checkout_id}", method="GET"
            )
        except Exception as e:
            _logger.exception(
                "Error fetching checkout details for %s: %s", tx_sudo.reference, e
            )
            tx_sudo._set_error(f"Failed to verify payment with EasyPay: {e}")
            return self._redirect_to_payment_status()

        # Handle frequent payment tokenization before processing
        if tx_sudo.provider_id._easypay_is_frequent(payment_data):
            payment_id = data.get("payment_id") or payment_data.get("payment", {}).get(
                "id"
            )
            if payment_id:
                tx_sudo._easypay_create_token(payment_id)

        try:
            tx_sudo._handle_notification_data("easypay", payment_data)
        except Exception as e:
            _logger.exception(
                "Error processing notification for %s: %s", tx_sudo.reference, e
            )

        return self._redirect_to_payment_status()

    @http.route(
        "/payment/easypay/checkout/cancel",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
    )
    def easypay_checkout_cancel(self, **data):
        reference = data.get("key") or data.get("reference")
        session_id = data.get("session_id")
        tx_sudo = self._find_transaction(session_id, reference)
        if tx_sudo:
            tx_sudo._set_canceled(state_message="Payment cancelled by customer")
        return self._redirect_to_payment_status()
