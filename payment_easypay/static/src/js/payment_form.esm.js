/* eslint-disable jsdoc/check-tag-names */
/* global document, window, console, fetch, setTimeout */
/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {rpc} from "@web/core/network/rpc";
import paymentForm from "@payment/js/payment_form";

paymentForm.include({
    easypayCheckoutInstance: null,

    async _processRedirectFlow(
        providerCode,
        paymentOptionId,
        paymentMethodCode,
        processingValues
    ) {
        if (providerCode !== "easypay") {
            return await this._super(...arguments);
        }

        // Check if this is Single Payment flow (has payment URL) or Checkout flow (has manifest)
        if (processingValues.easypay_payment_url) {
            // Single Payment - use standard redirect flow
            console.log(
                "EasyPay: Using Single Payment flow - redirecting to:",
                processingValues.easypay_payment_url
            );
            return await this._super(...arguments);
        }

        // Checkout flow - create session when user pays
        console.log("EasyPay: Using Checkout flow");
        const apiUrl = processingValues.api_url;

        if (!processingValues.easypay_use_checkout || !apiUrl) {
            console.error("EasyPay: Missing checkout configuration");
            this._displayErrorDialog(
                _t("Configuration Error"),
                _t("Missing payment configuration. Please try again.")
            );
            this._enableButton();
            return;
        }

        // Show loading message while creating session
        this._displayErrorDialog(
            _t("Preparing Payment"),
            _t("Creating secure payment session...")
        );

        try {
            // Create checkout session now (when user actually pays) using JSON-RPC
            const response_data = await rpc(
                "/payment/easypay/create_checkout_session",
                {
                    transaction_id: processingValues.reference,
                }
            );

            // Extract actual session data from JSON-RPC result
            const sessionData = response_data.result || response_data;
            if (!sessionData || sessionData.error) {
                throw new Error(sessionData?.error || "Invalid session response");
            }

            // Redirect to dedicated payment page with session data
            const paymentPageUrl = `/payment/easypay/checkout?session_id=${sessionData.checkout_id}&manifest=${encodeURIComponent(JSON.stringify(sessionData.checkout_manifest))}`;
            window.location.href = paymentPageUrl;
        } catch (error) {
            console.error("EasyPay: Failed to create checkout session", error);
            this._displayErrorDialog(
                _t("Payment Error"),
                _t("Failed to create payment session. Please try again.")
            );
            this._enableButton();
        }
    },

    async _initializeEasyPayCheckout(sessionData, processingValues) {
        const manifest = sessionData.checkout_manifest;
        const checkoutId = sessionData.checkout_id;

        const radio = document.querySelector('input[name="o_payment_radio"]:checked');
        const inlineForm = this._getInlineForm(radio);

        if (!inlineForm) {
            console.error("EasyPay: Inline form container not found");
            this._displayErrorDialog(
                _t("Configuration Error"),
                _t("Payment form container not found. Please try again.")
            );
            this._enableButton();
            return;
        }

        inlineForm.innerHTML = '<div id="easypay-checkout"></div>';

        try {
            // Debug: Check if SDK script is loading
            console.log("EasyPay: Checking SDK availability", {
                hasWindow: typeof window !== "undefined",
                hasEasypayCheckout: Boolean(window.easypayCheckout),
                scriptTags: document.querySelectorAll('script[src*="easypay"]').length,
                scriptsInHead: document.head.querySelectorAll("script").length,
            });

            // Wait for SDK to load from template script tag
            let attempts = 0;
            while (!window.easypayCheckout && attempts < 30) {
                await new Promise((resolve) => setTimeout(resolve, 100));
                attempts++;

                if (attempts % 10 === 0) {
                    console.log(
                        `EasyPay: Still waiting for SDK... attempt ${attempts}`
                    );
                }
            }

            // Fallback: Load SDK manually if template failed
            if (!window.easypayCheckout) {
                console.log("EasyPay: Template script failed, loading SDK manually");

                try {
                    const response = await fetch(
                        "https://cdn.easypay.pt/checkout/2.9.1/",
                        {method: "HEAD"}
                    );
                    console.log("EasyPay: CDN is reachable, status:", response.status);
                } catch (error) {
                    console.error("EasyPay: CDN not reachable", error);
                    this._displayErrorDialog(
                        _t("Network Error"),
                        _t(
                            "Unable to reach payment provider. Please check your internet connection."
                        )
                    );
                    this._enableButton();
                    return;
                }

                await new Promise((resolve, reject) => {
                    const script = document.createElement("script");
                    script.src = "https://cdn.easypay.pt/checkout/2.9.1/";
                    script.onload = () => {
                        console.log("EasyPay: Manual SDK load successful");
                        setTimeout(resolve, 500); // Give it time to initialize
                    };
                    script.onerror = (error) => {
                        console.error("EasyPay: Manual SDK load failed", error);
                        reject(error);
                    };
                    document.head.appendChild(script);
                });

                // Wait a bit more after manual load
                attempts = 0;
                while (!window.easypayCheckout && attempts < 20) {
                    await new Promise((resolve) => setTimeout(resolve, 100));
                    attempts++;
                }
            }

            if (!window.easypayCheckout) {
                console.error("EasyPay: SDK completely failed to load");
                this._displayErrorDialog(
                    _t("Payment Error"),
                    _t(
                        "Unable to load payment form. Please check your internet connection and refresh the page."
                    )
                );
                this._enableButton();
                return;
            }

            console.log("EasyPay: SDK loaded successfully");
            console.log("EasyPay: Manifest being passed to SDK:", manifest);
            console.log("EasyPay: Manifest type:", typeof manifest);
            console.log("EasyPay: Manifest has id:", Boolean(manifest.id));
            console.log("EasyPay: Manifest has session:", Boolean(manifest.session));
            console.log("EasyPay: Manifest has config:", Boolean(manifest.config));

            // Validate manifest structure before passing to SDK
            if (!manifest || typeof manifest !== "object") {
                console.error("EasyPay: Invalid manifest structure");
                this._displayErrorDialog(
                    _t("Configuration Error"),
                    _t("Invalid payment configuration. Please try again.")
                );
                this._enableButton();
                return;
            }

            if (!manifest.id || !manifest.session) {
                console.error("EasyPay: Missing required manifest fields");
                this._displayErrorDialog(
                    _t("Configuration Error"),
                    _t("Payment session is incomplete. Please try again.")
                );
                this._enableButton();
                return;
            }

            console.log("EasyPay: Manifest validation passed, initializing SDK");

            // Check if we should use test environment
            const isTestMode = processingValues.api_url.includes("test");
            console.log("EasyPay: Using test mode:", isTestMode);

            // Get user language for checkout localization
            const userLang = document.documentElement.lang || "en";
            const checkoutLanguage = userLang.startsWith("pt")
                ? "pt_PT"
                : userLang.startsWith("es")
                  ? "es_ES"
                  : "en";
            console.log("EasyPay: Using language:", checkoutLanguage);

            // Use SDK according to official documentation
            this.easypayCheckoutInstance = window.easypayCheckout.startCheckout(
                manifest,
                {
                    display: "inline",
                    testing: isTestMode, // ✅ Correct: Use test environment
                    language: checkoutLanguage,
                    onSuccess: (successInfo) => {
                        console.log("EasyPay: Payment success", successInfo);
                        window.location = `/payment/easypay/checkout/success?id=${checkoutId}`;
                    },
                    onError: (error) => {
                        console.error("EasyPay: Payment error", error);
                        console.log(
                            "EasyPay: Full error object:",
                            JSON.stringify(error, null, 2)
                        );
                        console.log("EasyPay: Error code:", error.code);
                        console.log("EasyPay: Error message:", error.message);

                        // Handle session expiration
                        if (error.code === "checkout-expired") {
                            console.log("EasyPay: Session expired detected");
                            console.log(
                                "EasyPay: NOT redirecting - showing debug info"
                            );
                            this._displayErrorDialog(
                                _t("Session Expired"),
                                _t("Payment session has expired. Please try again.")
                            );
                            this._enableButton();
                            return;
                        }

                        this._displayErrorDialog(
                            _t("Payment Error"),
                            _t(
                                "An error occurred during payment processing: " +
                                    (error.message || "Unknown error")
                            )
                        );
                        this._enableButton();
                    },
                    onClose: () => {
                        console.log("EasyPay: Checkout closed");
                        window.location = `/payment/easypay/checkout/cancel?id=${checkoutId}`;
                    },
                }
            );
        } catch (error) {
            console.error("EasyPay: Error initializing checkout", error);
            this._displayErrorDialog(
                _t("Payment Error"),
                _t("Could not initialize payment form. Please try again.")
            );
            this._enableButton();
        }

        return;
    },
});
