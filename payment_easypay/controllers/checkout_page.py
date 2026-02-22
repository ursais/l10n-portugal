# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json

from odoo import http
from odoo.http import request, route


class EasyPayCheckoutPageController(http.Controller):
    @route("/payment/easypay/checkout", type="http", auth="public")
    def checkout_page(self, **kwargs):
        """Dedicated page to host EasyPay checkout form."""
        session_id = kwargs.get("session_id")
        manifest_json = kwargs.get("manifest", {})
        if not session_id or not manifest_json:
            return "<h1>Error: Missing required parameters</h1>"
        # Decode manifest
        manifest = json.loads(manifest_json)
        # Render checkout page with template
        return request.render(
            "payment_easypay.checkout_page",
            {
                "session_id": session_id,
                "manifest": manifest,
                "manifest_json": manifest_json,
            },
        )
