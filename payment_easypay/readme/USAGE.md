Once configured, customers can use EasyPay to make payments:

1.  During checkout, select **EasyPay** as the payment method
2.  Click **Pay Now**
3.  A secure inline payment form loads. The customer selects a payment
    method and completes the payment without leaving the site.

## Payment method behaviour

- **Credit/Debit Card**: Payment is captured immediately. Order is
  confirmed as soon as the card is charged.
- **MB WAY**: The customer enters their mobile number. A push
  notification is sent to their phone for confirmation. The order is
  placed in *Pending* state until the user confirms (or rejects) on
  the MB WAY app.
- **Multibanco**: An ATM reference (Entity + Reference + Amount) is
  displayed. The customer pays at any ATM or via online banking. The
  order remains *Pending* until the payment is confirmed, which may
  take minutes to days. The customer should **not** close the
  confirmation page before noting down the reference.
- **Save payment details (tokenization)**: Logged-in customers can
  tick *Save my payment details* at checkout. The payment method is
  saved as a token for future charges (e.g. subscriptions).

## Test card details (test environment only)

- **Card number**: 4111 1111 1111 1111
- **CVV**: 123
- **Expiry**: any future date

See the [EasyPay Payment Methods guide](https://docs.easypay.pt/docs/guides/payment-methods)
for full test credentials for all payment methods.
