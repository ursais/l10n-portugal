# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class EasyPayCheckoutSessionController(http.Controller):
    @http.route(
        "/payment/easypay/create_checkout_session",
        type="json",
        auth="public",
        website=True,
    )
    def create_checkout_session(self, **kwargs):
        """Create checkout session when user actually clicks Pay."""
        # Extract transaction_id from JSON-RPC params
        transaction_id = kwargs.get("transaction_id")

        _logger.debug("[1/6] create_checkout_session called for tx=%s", transaction_id)
        if not transaction_id:
            _logger.error("Missing transaction_id in request. Params: %s", kwargs)
            return {"error": "Missing transaction_id"}

        # Get transaction by reference
        tx_sudo = (
            request.env["payment.transaction"]
            .sudo()
            .search(
                [
                    ("reference", "=", transaction_id),
                    ("provider_code", "=", "easypay"),
                ],
                limit=1,
            )
        )

        if not tx_sudo:
            _logger.error("Transaction not found: %s", transaction_id)
            return {"error": "Transaction not found"}
        _logger.debug(
            "[2/6] tx found: ref=%s state=%s checkout_id=%s tokenize=%s",
            tx_sudo.reference,
            tx_sudo.state,
            tx_sudo.easypay_checkout_id,
            tx_sudo.tokenize,
        )

        if tx_sudo.easypay_checkout_id and tx_sudo.state != "draft":
            # Session already created and payment is in progress — return the
            # existing session instead of creating a new one and losing the
            # webhook linkage for a payment the user may have already submitted.
            _logger.warning(
                "Checkout session already exists for transaction %s (state: %s); "
                "reusing existing session %s",
                transaction_id,
                tx_sudo.state,
                tx_sudo.easypay_checkout_id,
            )
            return {
                "error": "payment_in_progress",
                "message": (
                    "A payment is already in progress for this order. "
                    "If you requested a Multibanco reference, please use it to "
                    "complete your payment. Otherwise, please wait or refresh."
                ),
            }

        _logger.debug("[3/6] calling EasyPay POST /2.0/checkout")
        try:
            response = tx_sudo.provider_id._easypay_create_checkout_session(tx_sudo)
        except Exception as e:
            _logger.exception("Checkout session creation failed: %s", e)
            return {"error": str(e)}

        checkout_id = response.get("id")
        if not checkout_id:
            _logger.error(
                "EasyPay returned no checkout ID for transaction %s", transaction_id
            )
            return {"error": "Invalid session response: missing checkout ID"}

        tx_sudo.easypay_checkout_id = checkout_id
        _logger.debug(
            "[4/6] checkout session created: checkout_id=%s for tx=%s",
            checkout_id,
            tx_sudo.reference,
        )
        _logger.debug("[5/6] redirecting browser to /payment/easypay/checkout")

        return {
            "checkout_manifest": response,
            "checkout_id": checkout_id,
            "success": True,
        }
