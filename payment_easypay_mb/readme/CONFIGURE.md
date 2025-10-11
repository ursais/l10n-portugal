<<<<<<< HEAD
To configure this module, you need to:

1.  Ensure you have an active EasyPay account with Multibanco and/or MB
    WAY enabled
2.  Go to **Accounting \> Configuration \> Payment Providers**
3.  Select your EasyPay provider
4.  In the **Payment Method** field, select either:
    - **Multibanco** (mb)
    - **MB WAY** (mbw)
5.  Configure the webhook URL in your EasyPay dashboard (if not already
    done)
6.  Save the configuration
=======
To configure:

1.  Go to **Accounting \> Configuration \> Payment Providers** or
    **Website \> Configuration \> Payment Providers**
2.  Search for **EasyPay** and open the provider for **Multibanco** or
    **MB WAY**
3.  Fill in the required credentials:
    - **Account ID**: Your EasyPay Account ID (obtain from EasyPay
      dashboard)
    - **API Key**: Your EasyPay API Key (obtain from EasyPay dashboard)
4.  Configure the provider state:
    - Set to **Test Mode** to use the test environment
      (<https://api.test.easypay.pt>)
    - Set to **Enabled** to use the production environment
      (<https://api.prod.easypay.pt>)
5.  Save the configuration

For testing purposes, you can use the following credentials:

- **Account ID**: 2b0f63e2-9fb5-4e52-aca0-b4bf0339bbe6
- **API Key**: eae4aa59-8e5b-4ec2-887d-b02768481a92

**Note**: These test credentials only work in Test Mode. This module
depends on `payment_easypay`, hosted at
<https://github.com/oca/account-payment>.
>>>>>>> faeac50 ([ADD] payment_easypay_mb)
