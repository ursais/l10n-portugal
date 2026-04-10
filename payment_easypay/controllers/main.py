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

    @http.route(
        _return_url,
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
        save_session=False,
    )
    def _redirect_to_payment_status(self):
        """Standard redirect to payment status page."""
        return werkzeug.utils.redirect("/payment/status", code=303)

    def easypay_return_from_redirect(self, **data):
        """Process the return from EasyPay after payment."""
        # Parse JSON body if POST
        if (
            request.httprequest.method == "POST"
            and request.httprequest.content_type == "application/json"
        ):
            try:
                data = json.loads(request.httprequest.data.decode("utf-8"))
            except Exception:
                data = {}

        # Extract payment data from body or URL params
        reference = (
            data.get("key")
            or data.get("reference")
            or request.httprequest.args.get("key")
            or request.httprequest.args.get("reference")
        )

        if reference:
            tx_sudo = (
                request.env["payment.transaction"]
                .sudo()
                ._find_transaction_reference(reference)
            )
            if tx_sudo and tx_sudo.provider_id.code == "easypay":
                payment_id = data.get("id")
                if payment_id:
                    payment_data = tx_sudo.provider_id._easypay_make_request(
                        f"/2.0/single/{payment_id}", method="GET"
                    )
                    tx_sudo._handle_notification_data("easypay", payment_data)

        return self._redirect_to_payment_status()

    @http.route(
        _generic_webhook_url,
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def _generic_webhook(self):
        """Handle generic webhook from EasyPay."""
        try:
            data = json.loads(request.httprequest.data.decode("utf-8"))
        except Exception:
            data = {}

        reference = (
            data.get("key")
            or data.get("reference")
            or request.httprequest.args.get("key")
            or request.httprequest.args.get("reference")
        )

        if reference:
            tx_sudo = (
                request.env["payment.transaction"]
                .sudo()
                ._find_transaction_reference(reference)
            )
            if tx_sudo and tx_sudo.provider_id.code == "easypay":
                payment_id = data.get("id")
                if payment_id:
                    payment_data = tx_sudo.provider_id._easypay_make_request(
                        f"/2.0/single/{payment_id}", method="GET"
                    )
                    tx_sudo._handle_notification_data("easypay", payment_data)

        return self._redirect_to_payment_status()

    @http.route(
        _authorisation_webhook_url,
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def _authorisation_webhook(self, **kwargs):
        """Handle authorisation webhook from EasyPay."""
        try:
            data = json.loads(request.httprequest.data.decode("utf-8"))
        except Exception:
            data = kwargs

        tx_sudo = (
            request.env["payment.transaction"]
            .sudo()
            ._find_transaction_reference(data.get("key"))
        )
        if tx_sudo and tx_sudo.provider_id.code == "easypay":
            tx_sudo._handle_notification_data("easypay", data)

        return request.make_json_response({}, status=200)

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

    def _process_webhook_notification(self, data, webhook_type):
        payment_id = data.get("id")
        reference = data.get("key")
        notification_type = data.get("type")

        tx_sudo = self._find_transaction(payment_id, reference)
        if not tx_sudo:
            return request.make_json_response({}, status=200)

        try:
            payment_data = tx_sudo.provider_id._easypay_make_request(
                f"/2.0/authorisation/{payment_id}"
                if notification_type == "authorisation"
                else f"/2.0/single/{payment_id}",
                method="GET",
            )

            if (
                notification_type == "frequent"
                and payment_data.get("type") == "frequent"
            ):
                self._create_payment_token(tx_sudo, payment_id)

            tx_sudo._handle_notification_data("easypay", payment_data)
        except Exception as e:
            _logger.exception("Error processing webhook (%s): %s", webhook_type, e)

        return request.make_json_response({}, status=200)

    def _find_transaction(self, payment_id, reference):
        """Find transaction by reference or payment ID."""
        tx_sudo = request.env["payment.transaction"].sudo()
        if reference:
            return tx_sudo.search([("reference", "=", reference)], limit=1)
        elif payment_id:
            return tx_sudo.search(
                [
                    "|",
                    ("easypay_payment_id", "=", payment_id),
                    ("easypay_checkout_id", "=", payment_id),
                ],
                limit=1,
            )
        return None

    def _create_payment_token(self, tx_sudo, payment_id):
        """Create payment token for frequent payments."""
        token = (
            request.env["payment.token"]
            .sudo()
            .create(
                {
                    "provider_id": tx_sudo.provider_id.id,
                    "partner_id": tx_sudo.partner_id.id,
                    "provider_ref": payment_id,
                    "payment_method_id": tx_sudo.payment_method_id.id,
                    "payment_details": f"•••• {payment_id[-4:]}"
                    if len(payment_id) > 4
                    else payment_id,
                }
            )
        )
        tx_sudo.token_id = token.id
        _logger.info(
            "Payment token %s created for transaction %s", payment_id, tx_sudo.reference
        )

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

        domain = [("provider_code", "=", "easypay")]
        if reference:
            domain += [("reference", "=", reference)]
        elif checkout_id:
            domain += [("easypay_checkout_id", "=", checkout_id)]
        else:
            return self._redirect_to_payment_status()

        tx_sudo = request.env["payment.transaction"].sudo().search(domain, limit=1)
        if not tx_sudo:
            return self._redirect_to_payment_status()

        # Store client-side hints from onSuccess callback as early values
        if data.get("method"):
            tx_sudo.easypay_payment_method = data["method"]
        if data.get("status"):
            tx_sudo.easypay_capture_status = data["status"]

        try:
            payment_data = tx_sudo.provider_id._easypay_make_request(
                f"/2.0/checkout/{tx_sudo.easypay_checkout_id}", method="GET"
            )

            # Server-side data takes precedence over client-side hints
            payment_info = payment_data.get("payment", {})
            if payment_info:
                tx_sudo.easypay_payment_method = payment_info.get("method")
                tx_sudo.easypay_capture_status = payment_info.get("status")
                tx_sudo.easypay_payment_details = payment_data

            tx_sudo._handle_notification_data("easypay", payment_data)
        except Exception as e:
            _logger.exception(
                "Error fetching checkout details for %s: %s", tx_sudo.reference, e
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
        if reference:
            tx_sudo = (
                request.env["payment.transaction"]
                .sudo()
                .search([("reference", "=", reference)])
            )
            if tx_sudo:
                tx_sudo._set_canceled(state_message="Payment cancelled by customer")
        return self._redirect_to_payment_status()
