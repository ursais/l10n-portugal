/* global window, document, URLSearchParams */

(function () {
    "use strict";

    var data = window.easyPayData;
    var loadingEl = document.getElementById("payment-loading");
    var containerEl = document.getElementById("easypay-checkout-container");
    var errorEl = document.getElementById("payment-error");

    if (loadingEl) loadingEl.style.display = "none";

    if (!data || !window.easypayCheckout) {
        // SDK failed to load (onerror already showed error div) or missing data
        if (!data && errorEl) errorEl.style.display = "block";
        return;
    }

    if (containerEl) containerEl.style.display = "block";

    var sessionId = data.sessionId;
    var isTestMode = !data.apiUrl || data.apiUrl.includes("test");

    var checkoutInstance = window.easypayCheckout.startCheckout(data.manifest, {
        display: "inline",
        testing: isTestMode,
        onSuccess: function (successInfo) {
            var payment = (successInfo && successInfo.payment) || {};
            var params = new URLSearchParams({
                id: sessionId,
                method: payment.method || "",
                status: payment.status || "",
            });
            if (payment.id) {
                params.set("payment_id", payment.id);
            }
            checkoutInstance.unmount();
            window.location.href =
                "/payment/easypay/checkout/success?" + params.toString();
        },
        onError: function (error) {
            checkoutInstance.unmount();
            switch (error.code) {
                case "checkout-expired":
                    // Session expired - go back so user can restart and a new session is created
                    window.history.back();
                    break;
                case "already-paid":
                    window.location.href = "/payment/status";
                    break;
                case "checkout-canceled":
                    window.location.href =
                        "/payment/easypay/checkout/cancel?session_id=" + sessionId;
                    break;
                default:
                    if (errorEl) {
                        errorEl.querySelector("p").textContent =
                            "Payment error: " + (error.message || "Unknown error");
                        errorEl.style.display = "block";
                    }
                    if (containerEl) containerEl.style.display = "none";
            }
        },
        onPaymentError: function () {
            // Recoverable error - SDK keeps form open, user can retry
        },
        onClose: function () {
            checkoutInstance.unmount();
            window.location.href = "/payment/status";
        },
    });
})();
