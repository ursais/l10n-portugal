## EasyPay Backend Configuration

Before configuring the module in Odoo, you need to set up your EasyPay account and configure webhooks.

### 1. Create EasyPay Account

1.  **Test Environment**: Sign up at <https://backoffice.test.easypay.pt/>
2.  **Production**: Sign up at <https://www.easypay.pt/> and complete merchant verification
3.  Access your EasyPay dashboard and note your credentials:
    - **Account ID** (UUID format)
    - **API Key** (UUID format)

### 2. Configure Webhook in EasyPay Dashboard

To receive automatic payment status updates:

1.  Log in to your EasyPay dashboard
2.  Navigate to **Configuration > Webhooks** or **Settings > Notifications**
3.  Add a new webhook with these settings:
    - **URL**: `https://yourdomain.com/payment/easypay/webhook`
    - **Events**: Select all or at minimum:
        - Generic notifications
        - Transaction notifications
        - Authorisation notifications
    - **Method**: POST
    - **Content-Type**: application/json
4.  Save the webhook configuration

**Important**: Replace `yourdomain.com` with your actual Odoo domain.

### 3. Return URL Configuration

The return URL is automatically configured by Odoo for each payment:
- **Return URL**: `https://yourdomain.com/payment/easypay/return`

No manual configuration is needed in EasyPay dashboard as this URL is sent with each payment request.

## Odoo Configuration

After configuring EasyPay backend, configure the module in Odoo:

1.  Go to **Accounting \> Configuration \> Payment Providers** or
    **Website \> Configuration \> Payment Providers**
2.  Search for **EasyPay** and open the provider form
3.  Fill in the required credentials:
    - **Account ID**: Your EasyPay Account ID (from EasyPay dashboard)
    - **API Key**: Your EasyPay API Key (from EasyPay dashboard)
    - **Payment Method**: Select the payment method you want to use
      (Credit Card, Multibanco, MB WAY, etc.)
    - **Use Checkout**: Enable this to use EasyPay's integrated checkout
      experience (optional, for inline payment form)
4.  Configure the provider state:
    - Set to **Test Mode** to use the test environment
      (<https://api.test.easypay.pt>)
    - Set to **Enabled** to use the production environment
      (<https://api.prod.easypay.pt>)
5.  Save the configuration

For testing purposes, you can use the following credentials:

- **Account ID**: 2b0f63e2-9fb5-4e52-aca0-b4bf0339bbe6
- **API Key**: eae4aa59-8e5b-4ec2-887d-b02768481a92

**Note**: These test credentials only work in Test Mode.

## Webhook Configuration

To receive automatic payment status updates, configure the following
webhook URL in your EasyPay dashboard:

- **Webhook URL**: <https://yourdomain.com/payment/easypay/webhook>

This ensures that payment status changes are immediately reflected in
Odoo.

## Production Setup

### Get Production Credentials

1.  Sign up at <https://www.easypay.pt/>
2.  Complete merchant verification
3.  Get your production credentials from dashboard

### Configure for Production

1.  Open EasyPay provider in Odoo
2.  Update credentials with production values
3.  Change **State** to **Enabled**
4.  Configure webhook in EasyPay dashboard:

&nbsp;

    URL: https://yourdomain.com/payment/easypay/webhook
    Events: Generic, Transaction, Authorisation

5.  Test with real card (small amount)
6.  Publish the payment provider
