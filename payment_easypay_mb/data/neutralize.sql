-- Neutralize EasyPay Multibanco & MB WAY payment provider data
-- This script is executed when the database is neutralized (e.g., for testing or anonymization)

-- Disable EasyPay Multibanco and MB WAY payment providers and clear sensitive credentials
UPDATE payment_provider
SET state = 'disabled',
    easypay_account_id = NULL,
    easypay_api_key = NULL
WHERE code = 'easypay'
  AND easypay_payment_method IN ('mb', 'mbw');
