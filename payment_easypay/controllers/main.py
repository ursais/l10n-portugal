# Copyright 2025 Open Source Integrators
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

import werkzeug

from odoo import http
from odoo.http import request

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class EasyPayController(http.Controller):
    """Controller to handle EasyPay webhooks and redirects."""

    _generic_webhook_url = "/payment/easypay/webhook/generic"
    _authorisation_webhook_url = "/payment/easypay/webhook/authorisation"
    _transaction_webhook_url = "/payment/easypay/webhook/transaction"

    def _redirect_to_payment_status(self):
        """Standard redirect to payment status page."""
        return werkzeug.utils.redirect("/payment/status", code=303)

    @http.route(
        _generic_webhook_url,
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def _generic_webhook(self, **_kwargs):
        """Handle generic event webhook from EasyPay.

        Flat payload: {id, key, type, status, messages, date}
        'type' describes the event (capture, authorisation, etc.).
        'status: success' means the event completed successfully.
        """
        data = request.get_json_data()
        payment_id = data.get("id")
        reference = data.get("key")
        event_type = data.get("type")
        status = data.get("status")
        _logger.debug(
            "[W1] generic webhook: event=%s status=%s payment_id=%s reference=%s",
            event_type,
            status,
            payment_id,
            reference,
        )

        tx_sudo = self._find_transaction(payment_id, reference)
        if not tx_sudo:
            _logger.debug(
                "[W2] no transaction found for payment_id=%s reference=%s — ignoring",
                payment_id,
                reference,
            )
            return request.make_json_response({}, status=200)
        _logger.debug(
            "[W2] transaction found: ref=%s state=%s", tx_sudo.reference, tx_sudo.state
        )

        # Map event-specific 'success' to the correct payment status
        if status == "success" and event_type in ("capture", "transaction"):
            resolved_status = "paid"
        elif status == "success" and event_type == "authorisation":
            resolved_status = "authorised"
        else:
            resolved_status = status

        _logger.debug(
            "[W3] event=%s status=%s -> resolved_status=%s",
            event_type,
            status,
            resolved_status,
        )
        self._apply_transaction_status(tx_sudo, resolved_status, payment_id)
        return request.make_json_response({}, status=200)

    @http.route(
        _authorisation_webhook_url,
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def _authorisation_webhook(self, **_kwargs):
        """Handle authorisation webhook from EasyPay.

        Same flat payload shape as generic; 'success' means authorised.
        """
        data = request.get_json_data()
        payment_id = data.get("id")
        reference = data.get("key")
        status = data.get("status")
        _logger.debug(
            "[W1] authorisation webhook: status=%s payment_id=%s reference=%s",
            status,
            payment_id,
            reference,
        )

        tx_sudo = self._find_transaction(payment_id, reference)
        if not tx_sudo:
            _logger.debug(
                "[W2] no transaction found for payment_id=%s reference=%s — ignoring",
                payment_id,
                reference,
            )
            return request.make_json_response({}, status=200)

        resolved_status = "authorised" if status == "success" else status
        if resolved_status == "authorised" and tx_sudo.tokenize and payment_id:
            _logger.debug(
                "[W3] frequent payment authorised — creating token ref=%s", payment_id
            )
            tx_sudo._easypay_create_token(payment_id)
        self._apply_transaction_status(tx_sudo, resolved_status, payment_id)
        return request.make_json_response({}, status=200)

    @http.route(
        _transaction_webhook_url,
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def easypay_transaction_webhook(self, **_kwargs):
        """Handle transaction (capture detail) webhook from EasyPay.

        Nested payload: top-level id/key may be empty;
        reference and event type live inside the 'transaction' object.
        """
        data = request.get_json_data()
        tx_data = data.get("transaction", {})
        payment_id = data.get("id") or tx_data.get("id")
        reference = tx_data.get("key")
        event_type = tx_data.get("type")
        _logger.debug(
            "[W1] transaction webhook: event=%s payment_id=%s reference=%s",
            event_type,
            payment_id,
            reference,
        )

        tx_sudo = self._find_transaction(payment_id, reference)
        if not tx_sudo:
            _logger.debug(
                "[W2] no transaction found for payment_id=%s reference=%s — ignoring",
                payment_id,
                reference,
            )
            return request.make_json_response({}, status=200)

        resolved_status = "paid" if event_type == "capture" else None
        if resolved_status:
            self._apply_transaction_status(tx_sudo, resolved_status, payment_id)
        return request.make_json_response({}, status=200)

    def _apply_transaction_status(self, tx_sudo, status, payment_id):
        """Fetch full payment data from EasyPay and process the transaction state."""
        endpoint = (
            f"/2.0/checkout/{tx_sudo.easypay_checkout_id}"
            if tx_sudo.easypay_checkout_id
            else f"/2.0/single/{payment_id}"
            if payment_id
            else None
        )
        if not endpoint:
            _logger.debug(
                "[W3] no endpoint for tx=%s — applying status=%s directly",
                tx_sudo.reference,
                status,
            )
            tx_sudo._handle_notification_data("easypay", {"status": status})
            return

        _logger.debug("[W3] fetching payment data from %s", endpoint)
        try:
            payment_data = tx_sudo.provider_id._easypay_make_request(
                endpoint, method="GET"
            )
        except Exception as e:
            _logger.exception("Error fetching payment data: %s", e)
            tx_sudo._handle_notification_data("easypay", {"status": status})
            return

        payment_data["status"] = status
        _logger.debug(
            "[W4] payment data: status=%s method=%s",
            status,
            payment_data.get("payment", {}).get("method"),
        )

        _logger.debug(
            "[W6] dispatching for tx=%s (state=%s)", tx_sudo.reference, tx_sudo.state
        )
        try:
            tx_sudo._handle_notification_data("easypay", payment_data)
        except Exception as e:
            _logger.exception("Error processing notification data: %s", e)

        _logger.debug("[W7] done: tx=%s new state=%s", tx_sudo.reference, tx_sudo.state)

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
        _logger.debug(
            "[S1] checkout success callback: checkout_id=%s reference=%s",
            checkout_id,
            reference,
        )

        if not checkout_id and not reference:
            return self._redirect_to_payment_status()

        tx_sudo = self._find_transaction(checkout_id, reference)
        if not tx_sudo:
            _logger.debug(
                "[S2] no transaction found for checkout_id=%s reference=%s",
                checkout_id,
                reference,
            )
            return self._redirect_to_payment_status()
        _logger.debug(
            "[S2] transaction found: ref=%s state=%s",
            tx_sudo.reference,
            tx_sudo.state,
        )

        # ── Async payment methods ──────────────────────────────────────
        # Redirect to a method-specific page instead of the generic
        # /payment/status spinner.
        method = data.get("method", "").upper()

        # Multibanco: show entity / reference / amount.
        # NOTE: entity/reference come from the client-side SDK callback.
        # They are stored for display purposes only; the authoritative
        # payment confirmation always comes through the webhook.
        entity = data.get("entity")
        mb_reference = data.get("mb_reference")
        if method == "MB" and entity and mb_reference:
            tx_sudo.easypay_mb_entity = entity
            tx_sudo.easypay_mb_reference = mb_reference
            tx_sudo.easypay_mb_expiration = data.get("expiration", "")
            tx_sudo._set_pending()
            access_token = payment_utils.generate_access_token(tx_sudo.id)
            _logger.debug(
                "[S3] MB payment — redirecting to reference page: "
                "entity=%s reference=%s expiration=%s",
                entity,
                mb_reference,
                tx_sudo.easypay_mb_expiration,
            )
            return request.redirect(
                f"/payment/easypay/mb_reference/{tx_sudo.id}"
                f"?access_token={access_token}"
            )

        # ── All other methods (CC, MB WAY, etc.) ─────────────────────
        # Try to confirm synchronously by fetching the checkout status
        # from EasyPay.  If that already reports success we process
        # immediately; otherwise we set pending and let the webhook
        # handle the final confirmation.
        _logger.debug("[S3] fetching /2.0/checkout/%s", tx_sudo.easypay_checkout_id)
        try:
            payment_data = tx_sudo.provider_id._easypay_make_request(
                f"/2.0/checkout/{tx_sudo.easypay_checkout_id}", method="GET"
            )
        except Exception as e:
            _logger.warning(
                "[S3] could not fetch checkout for %s: %s "
                "— setting pending, webhook will confirm.",
                tx_sudo.reference,
                e,
            )
            tx_sudo._set_pending()
            return self._redirect_to_payment_status()

        _logger.debug(
            "[S4] checkout data: checkout_status=%s payment_status=%s method=%s",
            payment_data.get("status"),
            payment_data.get("payment", {}).get("status"),
            payment_data.get("payment", {}).get("method"),
        )
        try:
            tx_sudo._handle_notification_data("easypay", payment_data)
        except Exception as e:
            _logger.exception(
                "[S4] error processing notification for %s: %s",
                tx_sudo.reference,
                e,
            )

        _logger.debug(
            "[S5] redirecting to /payment/status — tx=%s state=%s",
            tx_sudo.reference,
            tx_sudo.state,
        )
        return self._redirect_to_payment_status()

    @http.route(
        "/payment/easypay/mb_reference/<int:tx_id>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        website=True,
        save_session=False,
    )
    def easypay_mb_reference(self, tx_id, access_token=None, **_kwargs):
        """Display Multibanco payment reference details."""
        if not payment_utils.check_access_token(access_token, tx_id):
            raise werkzeug.exceptions.Forbidden()
        tx_sudo = request.env["payment.transaction"].sudo().browse(tx_id).exists()
        if not tx_sudo or not tx_sudo.easypay_mb_entity:
            return request.redirect("/payment/status")
        # Format reference as "xxx xxx xxx" groups of 3 digits
        raw_ref = tx_sudo.easypay_mb_reference or ""
        digits = raw_ref.replace(" ", "")
        formatted_ref = " ".join(digits[i : i + 3] for i in range(0, len(digits), 3))
        return request.render(
            "payment_easypay.mb_reference_page",
            {
                "tx": tx_sudo,
                "entity": tx_sudo.easypay_mb_entity,
                "reference": formatted_ref,
                "amount": tx_sudo.amount,
                "currency": tx_sudo.currency_id,
                "expiration": tx_sudo.easypay_mb_expiration,
                "redirect_url": tx_sudo.landing_route or "/my/home",
            },
        )

    @http.route(
        "/payment/easypay/checkout/cancel",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
    )
    def easypay_checkout_cancel(self, **data):
        """Handle checkout cancellation from EasyPay SDK."""
        reference = data.get("key") or data.get("reference")
        session_id = data.get("session_id")
        tx_sudo = self._find_transaction(session_id, reference)
        if tx_sudo:
            tx_sudo._set_canceled(state_message="Payment cancelled by customer")
        return self._redirect_to_payment_status()
