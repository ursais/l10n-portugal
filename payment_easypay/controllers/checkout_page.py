# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json
import logging

from markupsafe import Markup

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class EasyPayCheckoutPageController(http.Controller):
    @http.route(
        "/payment/easypay/checkout",
        type="http",
        auth="public",
        csrf=False,
        save_session=False,
    )
    def checkout_page(self, **kwargs):
        """Dedicated page to host EasyPay checkout form."""
        session_id = kwargs.get("session_id")
        manifest_json = kwargs.get("manifest")

        if not session_id or not manifest_json:
            return request.redirect("/payment/status")

        try:
            manifest = json.loads(manifest_json)
        except json.JSONDecodeError:
            _logger.warning("Failed to parse checkout manifest from URL params")
            return request.redirect("/payment/status")

        # Find the transaction to derive api_url server-side
        tx_sudo = (
            request.env["payment.transaction"]
            .sudo()
            .search(
                [
                    ("easypay_checkout_id", "=", session_id),
                    ("provider_code", "=", "easypay"),
                ],
                limit=1,
            )
        )
        api_url = tx_sudo.provider_id._easypay_get_api_url() if tx_sudo else ""

        # Serialise the entire JS data object server-side so the template
        # never interpolates untrusted strings inside a <script> block.
        easypay_data_json = Markup(
            json.dumps(
                {"sessionId": session_id, "manifest": manifest, "apiUrl": api_url}
            )
        )

        return request.render(
            "payment_easypay.checkout_page",
            {"easypay_data_json": easypay_data_json},
        )
