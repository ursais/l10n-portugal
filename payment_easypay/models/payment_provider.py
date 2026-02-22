# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from .. import const
from .. import utils as easypay_utils
from ..controllers.main import EasyPayController

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("easypay", "EasyPay")], ondelete={"easypay": "set default"}
    )
    easypay_account_id = fields.Char(
        string="Account ID",
        help="The Account ID provided by EasyPay",
    )
    easypay_api_key = fields.Char(
        string="API Key",
        help="The API Key provided by EasyPay",
        groups="base.group_system",
    )
    easypay_payment_method_ids = fields.Many2many(
        comodel_name="easypay.payment.method",
        string="Payment Methods",
        help="Select the payment methods to enable for EasyPay",
        default=lambda self: self.env["easypay.payment.method"].search(
            [("code", "=", "cc")]
        ),
    )
    easypay_use_checkout = fields.Boolean(
        string="Use Checkout",
        default=False,
        help="Use EasyPay Checkout for a better user experience",
    )
    easypay_payment_type = fields.Selection(
        [
            ("single", "Single Payment"),
            ("frequent", "Frequent Payment (Tokenization)"),
        ],
        string="Payment Type",
        default="single",
        required_if_provider="easypay",
        help="Single: One-time payment. Frequent: Save payment details for future use.",
    )
    easypay_webhook_base_url = fields.Char(
        string="Webhook Base URL",
        help="Base URL that will be used for webhook configuration in EasyPay",
        compute="_compute_easypay_webhook_base_url",
    )

    # === COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """Override of `payment` to enable additional features."""
        res = super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == "easypay").update(
            {
                "support_manual_capture": "full_only",
                "support_refund": "partial",
            }
        )
        return res

    def _compute_easypay_webhook_base_url(self):
        """Compute the base URL that will be used for webhook configuration."""
        for provider in self:
            if provider.code == "easypay":
                provider.easypay_webhook_base_url = provider.get_base_url()
            else:
                provider.easypay_webhook_base_url = False

    def _easypay_get_inline_form_values(self, amount, currency, partner_id, tx_sudo):
        """Return the inline form values for EasyPay Checkout.

        Note: self.ensure_one()

        :param float amount: The transaction amount
        :param res.currency currency: The transaction currency
        :param res.partner partner_id: The transaction partner
        :param payment.transaction tx_sudo: The sudoed transaction
        :return: The inline form values
        :rtype: str (JSON)
        """
        self.ensure_one()

        if self.easypay_use_checkout:
            response = self._easypay_create_checkout_session(tx_sudo)
            tx_sudo.easypay_checkout_id = response.get("id")

            import json

            return json.dumps(
                {
                    "checkout_manifest": response.get("session"),
                    "checkout_id": response.get("id"),
                    "api_url": self._easypay_get_api_url(),
                }
            )

        return json.dumps({})

    # === BUSINESS METHODS - GETTERS ===#

    def _get_default_payment_method_codes(self):
        """Override of `payment` to return the default payment method codes."""
        default_codes = super()._get_default_payment_method_codes()
        if self.code != "easypay":
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _get_available_tokens(
        self, providers_ids, partner_id, is_validation=False, **kwargs
    ):
        if self.code != "easypay":
            return super()._get_available_tokens(
                providers_ids, partner_id, is_validation, **kwargs
            )

        domain = [("provider_ref", "!=", False)]
        if not is_validation:
            domain += [
                ("provider_id", "in", providers_ids),
                ("partner_id", "=", partner_id),
            ]
        else:
            partner = self.env["res.partner"].browse(partner_id)
            domain += [
                ("partner_id", "in", [partner.id, partner.commercial_partner_id.id])
            ]

        return self.env["payment.token"].search(domain)

    def _easypay_get_api_url(self):
        return const.API_URL_PROD if self.state == "enabled" else const.API_URL_TEST

    # === BUSINESS METHODS - PAYMENT FLOW ===#

    def _easypay_make_request(self, endpoint, payload=None, method="POST"):
        url = f"{self._easypay_get_api_url()}{endpoint}"
        headers = {
            "AccountId": self.easypay_account_id,
            "ApiKey": self.easypay_api_key,
            "Content-Type": "application/json",
        }

        try:
            response = getattr(requests, method.lower())(
                url,
                json=payload if method in ["POST", "PATCH"] else None,
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error("EasyPay API request failed: %s", e)
            raise ValidationError(_("EasyPay API request failed: %s", str(e))) from None

    def _easypay_create_checkout_session(self, tx_sudo):
        """Create EasyPay checkout session for the transaction."""
        if tx_sudo.currency_id.name != "EUR":
            raise ValidationError(
                _("EasyPay only supports EUR currency for checkout payments.")
            )

        items = self._build_order_items(tx_sudo)

        # Get payment methods for checkout
        payment_methods = self.easypay_payment_method_ids
        if not payment_methods:
            # Fallback to credit card if no methods selected
            payment_methods = self.env["easypay.payment.method"].search(
                [("code", "=", "cc")]
            )

        method_codes = [method.code for method in payment_methods]
        payment_type = self.easypay_payment_type or "single"

        # Build base payload
        payload = {
            "type": [payment_type],
            "payment": {
                "methods": method_codes,
                "currency": tx_sudo.currency_id.name,
            },
            "order": {
                "key": tx_sudo.reference,
                "value": tx_sudo.amount,
                "items": items,
            },
            "customer": easypay_utils.include_customer_data(tx_sudo),
        }

        # Add capture object for payments
        capture_config = {
            "descriptive": tx_sudo.reference,
            "transaction_key": tx_sudo.reference,
        }
        payload["payment"]["capture"] = capture_config
        payload["payment"]["type"] = (
            const.PAYMENT_TYPE_SALE
            if payment_type == "single"
            else const.PAYMENT_TYPE_AUTHORISATION
        )

        return self._easypay_make_request("/2.0/checkout", payload)

    def _build_order_items(self, tx_sudo):
        """Extract order items from transaction."""
        # Try to get items from sale order
        if hasattr(tx_sudo, "sale_order_ids") and tx_sudo.sale_order_ids:
            order = tx_sudo.sale_order_ids[0]
            return self._build_items_from_lines(order.order_line)

        # Try to get items from invoice
        if hasattr(tx_sudo, "invoice_ids") and tx_sudo.invoice_ids:
            invoice = tx_sudo.invoice_ids[0]
            return self._build_items_from_lines(invoice.invoice_line_ids)

        # Fallback to generic payment item
        return [
            {
                "description": f"Payment for {tx_sudo.reference}",
                "quantity": 1,
                "key": tx_sudo.reference,
                "value": tx_sudo.amount,
            }
        ]

    def _build_items_from_lines(self, lines):
        """Build order items from line records."""
        return [
            {
                "description": line.product_id.name or line.name,
                "quantity": int(
                    line.product_uom_qty
                    if hasattr(line, "product_uom_qty")
                    else line.quantity
                ),
                "key": str(line.id),
                "value": float(line.price_total),
            }
            for line in lines
        ]

    def _easypay_create_single_payment(self, tx_sudo):
        """Create EasyPay single payment for the transaction."""
        return_url = f"{tx_sudo.provider_id.get_base_url()}/payment/easypay/return"
        payload = {
            "type": const.PAYMENT_TYPE_SALE,
            "method": "cc",
            "value": tx_sudo.amount,
            "currency": tx_sudo.currency_id.name,
            "key": tx_sudo.reference,
            "capture": {
                "descriptive": tx_sudo.reference,
                "transaction_key": tx_sudo.reference,
            },
            "customer": easypay_utils.include_customer_data(tx_sudo),
            "return_url": return_url,
        }
        return self._easypay_make_request("/2.0/single", payload)

    def action_easypay_test_connection(self):
        """Test connection to EasyPay API using ping endpoint."""
        self.ensure_one()

        if not self.easypay_account_id or not self.easypay_api_key:
            return self._notify_user(
                "Please fill in Account ID and API Key first.", "warning"
            )

        try:
            response = self._easypay_make_request("/2.0/system/ping", method="GET")
            if response and response.get("environment"):
                return self._notify_user(
                    "Connection successful! EasyPay API is reachable.", "success"
                )
            else:
                return self._notify_user(
                    "Connection test failed. Please check your credentials.", "danger"
                )
        except Exception as e:
            _logger.exception("EasyPay connection test failed: %s", e)
            return self._notify_user(f"Connection test failed: {str(e)}", "danger")

    def action_easypay_configure_webhooks(self):
        if not self.easypay_api_key or not self.easypay_account_id:
            return self._notify_user(
                "You cannot configure webhooks without setting your EasyPay API "
                "credentials first.",
                "danger",
            )

        base_url = self.get_base_url()
        webhook_urls = {
            "generic": f"{base_url}{EasyPayController._generic_webhook_url}",
            "authorisation": (
                f"{base_url}{EasyPayController._authorisation_webhook_url}"
            ),
            "transaction": f"{base_url}{EasyPayController._transaction_webhook_url}",
            "visa_fwd": f"{base_url}{EasyPayController._return_url}",
            "visa_detail": f"{base_url}{EasyPayController._return_url}",
        }

        try:
            self._easypay_make_request(
                "/2.0/config", payload=webhook_urls, method="PATCH"
            )
            return self._notify_user("Webhooks configured successfully!", "success")
        except Exception as e:
            _logger.exception("Error configuring webhooks: %s", e)
            return self._notify_user(
                "Error configuring webhooks. Please check your API credentials.",
                "danger",
            )

    def _notify_user(self, message, notification_type):
        """Helper method to notify user with feedback."""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": message,
                "type": notification_type,
                "sticky": notification_type == "danger",
            },
        }
