# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import http
from odoo.http import request, route

_logger = logging.getLogger(__name__)


class EasyPayCheckoutSessionController(http.Controller):
    @route(
        "/payment/easypay/create_checkout_session",
        type="json",
        auth="public",
        website=True,
    )
    def create_checkout_session(self, **kwargs):
        """Create checkout session when user actually clicks Pay."""
        # Extract transaction_id from JSON-RPC params
        transaction_id = kwargs.get("transaction_id")

        if not transaction_id:
            _logger.error("Missing transaction_id in request. Params: %s", kwargs)
            return {"error": "Missing transaction_id"}

        # Get transaction by reference
        try:
            tx_sudo = (
                request.env["payment.transaction"]
                .sudo()
                .search([("reference", "=", transaction_id)], limit=1)
            )
        except Exception as e:
            _logger.error("Checkout session creation failed: %s", str(e))
            return {"error": str(e)}

        if not tx_sudo:
            _logger.error("Transaction not found: %s", transaction_id)
            return {"error": "Transaction not found"}

        # Create checkout session
        response = tx_sudo.provider_id._easypay_create_checkout_session(tx_sudo)

        # Store checkout ID
        tx_sudo.easypay_checkout_id = response.get("id")

        return {
            "checkout_manifest": response,
            "checkout_id": response.get("id"),
            "success": True,
        }
