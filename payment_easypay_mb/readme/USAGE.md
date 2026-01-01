<<<<<<< HEAD
## Installation

1.  Install `payment_easypay` module first
2.  Install `payment_easypay_mb` module
3.  Restart Odoo server (if needed)

## Configuration

1.  Go to **Accounting \> Configuration \> Payment Providers**
2.  Open your EasyPay provider
3.  In **Payment Method** field, you can now select:
    - **Multibanco** (mb) - For ATM/online banking payments
    - **MB WAY** (mbw) - For mobile payments
4.  Save the configuration

=======
>>>>>>> faeac50 ([ADD] payment_easypay_mb)
## Testing

### Multibanco Test

1.  Create a test sale order
2.  Select EasyPay as payment method
3.  Customer will receive Multibanco reference:
    - Entity
    - Reference
    - Amount
    - Expiry date
4.  Test payment using EasyPay test environment

### MB WAY Test

1.  Create a test sale order
2.  Select EasyPay as payment method
3.  Customer enters phone number
4.  Push notification sent to MB WAY app
5.  Confirm payment in app

## Production Use

1.  Ensure your EasyPay account has Multibanco and/or MB WAY enabled
<<<<<<< HEAD

2.  Set provider **State** to **Enabled**

3.  Configure webhook URL in EasyPay dashboard:

        https://yourdomain.com/payment/easypay/webhook

4.  Test with small real transactions before going live

## Important Notes
=======
2.  Set provider **State** to **Enabled**
3.  Configure webhook URL in EasyPay dashboard:

&nbsp;

    https://yourdomain.com/payment/easypay/webhook

4.  Test with small real transactions before going live

### Important Notes
>>>>>>> faeac50 ([ADD] payment_easypay_mb)

- Multibanco payments may take a few minutes to confirm
- MB WAY requires a valid Portuguese phone number
- Both methods support the same webhook notifications as credit card
  payments
- The same EasyPay API endpoints are used - the payment method is
  specified in the request
