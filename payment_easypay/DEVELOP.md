# EasyPay Odoo Module - Development Guide

## Overview

This module provides integration between Odoo and EasyPay Checkout, a pre-built payment
form that handles the entire payment flow including customer information collection,
payment method selection, invoking payment APIs, and displaying payment feedback.

**Supported payment methods:** Credit/Debit Cards, MB WAY, Multibanco, SEPA Direct
Debit, Virtual IBAN, Apple Pay, Google Pay, Samsung Pay

**Supported payment types:** Single, Frequent (tokenization), Subscription

## Architecture

### Core Components

- **Payment Provider** (`models/payment_provider.py`) - Provider configuration, API
  integration, and checkout session creation
- **Payment Transaction** (`models/payment_transaction.py`) - Transaction handling and
  state management
- **Controllers** (`controllers/`) - Webhook handling and checkout endpoints
- **Custom Payment Methods** (`models/easypay_payment_method.py`) - EasyPay-specific
  payment methods (cc, mb, mbw, etc.)
- **Frontend Integration** (`static/src/js/`) - Checkout SDK initialization and RPC
  calls

## Checkout Workflow

### 1. User Initiates Payment

**User Action:** Selects EasyPay payment method and clicks "Pay"

**Odoo Events:**

- Payment transaction created (`payment.transaction`)
- `_get_specific_processing_values()` called
- `_get_specific_rendering_values()` called
- Checkout template rendered, JavaScript loads and waits for user to click Pay

### 2. Checkout Session Creation (Server-Side)

**Odoo Server:**

- Browser calls `/payment/easypay/create_checkout_session` via JSON-RPC
- `_easypay_create_checkout_session()` builds the payload and calls EasyPay API
- API call: `POST https://api.test.easypay.pt/2.0/checkout` (test) or
  `https://api.prod.easypay.pt/2.0/checkout` (production)
- Response (the **checkout manifest**):
  `{"id": "57cc19e9-...", "session": "8zoaBOC0Mj5Mg_Y...", "config": null}`
- The checkout manifest is passed **directly** to `startCheckout()` — do not modify it
- `easypay_checkout_id` stored on transaction

**EasyPay Server:**

- Creates checkout session with the requested payment methods
- Returns the manifest used to initialize the SDK

> ⚠️ **Security:** Sessions must always be created server-side. Never expose API keys in
> client code.

### 3. SDK Initialization (Client-Side)

**Browser:**

- EasyPay SDK loaded from CDN: `https://cdn.easypay.pt/checkout/2.9.1/`
- `easypayCheckout.startCheckout(manifest, options)` called
- Payment form rendered inline in `#easypay-checkout` container
- `testing: true` must be set when using the test API (`api.test.easypay.pt`)

### 4. User Selects Payment Method & Pays

**User Action:** Chooses a payment method and submits payment details

**EasyPay SDK:**

- Displays method-specific form fields
- Invokes payment APIs on the EasyPay side
- Displays payment feedback inline

### 5. Payment Processing

#### Card Payments (Immediate Capture)

- User enters card details in SDK form
- EasyPay processes and captures the payment immediately
- SDK calls `onSuccess` with status: `paid` or `authorised`

#### Multibanco (Delayed Capture)

- EasyPay generates a Multibanco payment reference
- SDK calls `onSuccess` with status: `pending`
- User must separately pay using ATM or online banking
- Funds arrive asynchronously; confirmed via webhook

#### MB WAY (Mobile-Initiated)

- User provides phone number in SDK form
- MB WAY push notification sent to customer's device
- SDK calls `onSuccess` with status: `paid` or `pending`

#### Frequent Payment (Tokenization)

- SDK calls `onSuccess` with a payment ID to store for future captures
- Later captures done via `POST /capture/:id`

### 6. SDK Event Handlers

```javascript
startCheckout(manifest, {
  display: "inline", // or "popup" (popup requires id: "button-element-id")
  testing: true, // remove in production
  language: "pt_PT", // "en", "pt_PT", "es_ES" — auto-detected if omitted
  onSuccess: (checkoutInfo) => {
    // Payment completed - checkoutInfo.payment has details
    // In frequent flow: save checkoutInfo.payment.id for later captures
  },
  onError: (error) => {
    // Unrecoverable error — checkout cannot continue
    // error.code === 'checkout-expired': must create a new session
  },
  onPaymentError: (error) => {
    // Recoverable error — informative only
    // SDK keeps form open; user can retry with same or different method
    // error has both 'code' and 'checkout' (same shape as onSuccess checkoutInfo)
  },
  onClose: () => {
    // User dismissed the form — NOT a payment failure or cancellation
    // Clean up or redirect to payment status page
  },
});
```

> ⚠️ **Popup mode** requires passing `id` of the trigger button element:
> `startCheckout(manifest, { id: "checkout-button", display: "popup" })`

> ⚠️ **Session Expiration:** Checkout sessions expire after **30 minutes**. Handle
> `checkout-expired` in `onError` by creating a new session.

### 7. Success Callback Data

```javascript
checkoutInfo = {
    type: "single|frequent|subscription",  // top-level payment type
    payment: {
        id: "...",                    // Payment ID — save this for future captures (frequent flow)
        method: "cc|mb|mbw|dd|...",   // Selected payment method (same codes as checkout creation)
        status: "paid|pending|...",   // See status values below
        brand: "VISA|MasterCard",     // Card only
        expiration: "MM/YY",          // Card: 'MM/YY'; Multibanco: 'Y-m-d H:i'
        sddMandate: { ... },          // SEPA Direct Debit only
    }
}
```

Possible `payment.status` values: `authorised`, `deleted`, `enrolled`, `error`,
`failed`, `paid`, `pending`, `success`, `tokenized` (frequent only), `voided`

> Note: `type` is a **top-level** field on `checkoutInfo`, not inside `payment`.

> ⚠️ **Important:** Do **not** rely solely on the client-side `onSuccess` callback for
> critical business logic. Always verify payment status on the server using webhooks or
> the API.

### 8. Post-Payment Redirect

**Browser:**

- After `onSuccess`, redirects to
  `/payment/easypay/checkout/success?id={session_id}&method={method}&status={status}`
- After `onClose`, redirects to `/payment/status` (standard Odoo page — `onClose` is not
  a cancellation)
- The `/checkout/cancel` route is only used if EasyPay explicitly cancels the payment
  server-side

**Odoo Server:**

- `easypay_checkout_success()` handler called
- Fetches full payment details: `GET /2.0/checkout/{session_id}`
- Updates transaction with:
  - `easypay_payment_method` (selected method)
  - `easypay_capture_status` (capture status)
  - `easypay_payment_details` (full response)
- Calls `_handle_notification_data()` to update Odoo transaction state

### 9. Webhook Processing (Async - Critical for Multibanco)

**EasyPay Server** notifies Odoo asynchronously:

- `POST /payment/easypay/webhook/generic`
- `POST /payment/easypay/webhook/authorisation`
- `POST /payment/easypay/webhook/transaction`

**Odoo Server:**

- Validates notification data
- Fetches latest payment details from EasyPay API
- Updates transaction state (e.g., `pending` → `done` for Multibanco)

## Complete Flow Timeline

```
User Clicks Pay
  → Browser calls /create_checkout_session (RPC)
    → Odoo calls POST /2.0/checkout (EasyPay API)
      → Manifest returned to browser
        → SDK initializes and renders payment form
          → User selects method and pays
            → SDK onSuccess fires
              → Browser redirects to /checkout/success
                → Odoo calls GET /2.0/checkout/{id}
                  → Transaction state updated
                    → (Async) Webhook confirms or updates state
```

## Capture Status Differences

| Method            | Capture Timing            | Status after `onSuccess`         |
| ----------------- | ------------------------- | -------------------------------- |
| Card              | Immediate                 | `paid` or `authorised`           |
| MB WAY            | Immediate                 | `paid`                           |
| Multibanco        | Delayed (user pays later) | `pending` → `paid` (via webhook) |
| SEPA Direct Debit | Delayed                   | `pending`                        |

## Data Storage

### Transaction Fields

| Field                     | Description                                      |
| ------------------------- | ------------------------------------------------ |
| `easypay_payment_id`      | Payment ID from EasyPay                          |
| `easypay_checkout_id`     | Checkout session identifier                      |
| `easypay_payment_method`  | Method selected by user (cc, mb, mbw, etc.)      |
| `easypay_capture_status`  | Capture status (paid, pending, authorised, etc.) |
| `easypay_payment_details` | Full JSON response from EasyPay                  |
| `easypay_payment_url`     | Redirect URL (non-checkout flow)                 |

### Provider Configuration Fields

| Field                        | Description                            |
| ---------------------------- | -------------------------------------- |
| `easypay_account_id`         | EasyPay account identifier             |
| `easypay_api_key`            | API key for authentication (encrypted) |
| `easypay_payment_method_ids` | Available payment methods              |
| `easypay_use_checkout`       | Enable checkout flow                   |
| `easypay_payment_type`       | Single vs frequent payments            |

## API Endpoints

### EasyPay API

| Endpoint                            | Description                                                           |
| ----------------------------------- | --------------------------------------------------------------------- |
| `POST /2.0/checkout`                | Create checkout session                                               |
| `GET /2.0/checkout/{id}`            | Get checkout details                                                  |
| `POST /2.0/single`                  | Create single payment (non-checkout flow)                             |
| `GET /2.0/single/{id}`              | Get payment details                                                   |
| `POST /2.0/capture/:id`             | Capture frequent payment (body: `{"value": ..., "descriptive": ...}`) |
| `POST /2.0/capture/{id}/refund`     | Process refund                                                        |
| `POST /2.0/authorisation/{id}/void` | Void authorized payment                                               |

### Odoo Controllers

| Route                                      | Description                       |
| ------------------------------------------ | --------------------------------- |
| `/payment/easypay/create_checkout_session` | Create EasyPay session (JSON-RPC) |
| `/payment/easypay/checkout/success`        | Post-payment redirect handler     |
| `/payment/easypay/checkout/cancel`         | Cancellation redirect handler     |
| `/payment/easypay/webhook/generic`         | Generic webhook                   |
| `/payment/easypay/webhook/authorisation`   | Authorisation webhook             |
| `/payment/easypay/webhook/transaction`     | Transaction webhook               |

## Configuration

### Provider Setup

1. Create EasyPay payment provider in Odoo (Accounting → Configuration → Payment
   Providers)
2. Configure **Account ID** and **API Key** from EasyPay backoffice
3. Select available payment methods
4. Enable **Use Checkout** to use the SDK-based flow
5. Configure **Payment Type** (single or frequent)
6. Click **Configure Webhooks** to register Odoo webhook URLs with EasyPay

### Payment Method Codes (EasyPay API)

| Code  | Method            |
| ----- | ----------------- |
| `cc`  | Credit/Debit Card |
| `mb`  | Multibanco        |
| `mbw` | MB WAY            |
| `dd`  | SEPA Direct Debit |
| `vi`  | Virtual IBAN      |
| `ap`  | Apple Pay         |
| `gp`  | Google Pay        |
| `sw`  | Samsung Pay       |

## Testing

- Use test environment: `https://api.test.easypay.pt`
- Always pass `testing: true` to `startCheckout` when using the test API
- Remove `testing: true` before going to production
- Test cards and payment methods available in
  [EasyPay Payment Methods guide](https://docs.easypay.pt/docs/guides/payment-methods)

## Best Practices (from official EasyPay docs)

1. **Always create sessions server-side** — never expose API keys in client code
2. **Handle all error cases** — including `checkout-expired` to re-create sessions
3. **Use webhooks** — do not rely solely on client-side callbacks for payment
   confirmation
4. **Verify payments server-side** — always cross-check via EasyPay API
5. **Customize for your brand** — match Checkout to your website's look and feel
6. **Test thoroughly** — use test environment before going live
7. **Mobile first** — test on various devices and screen sizes

## Troubleshooting

| Issue                                          | Solution                                                               |
| ---------------------------------------------- | ---------------------------------------------------------------------- |
| "This payment method needs a partner in crime" | Ensure payment methods are linked to an enabled provider               |
| Checkout SDK not loading                       | Check CDN availability; verify `testing` flag matches API environment  |
| `checkout-expired` error                       | Create a new checkout session and re-initialize the SDK                |
| Multibanco payment not confirmed               | Check webhook delivery; Multibanco is async and requires webhooks      |
| Payment status not updating                    | Check webhook URLs are accessible and registered in EasyPay backoffice |
| `transaction_id` missing in session creation   | Ensure the transaction reference is passed correctly via RPC           |
