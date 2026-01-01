## Technical Documentation: Multibanco & MB WAY Implementation

### Overview

This module implements Multibanco and MB WAY payment processing through
the EasyPay API. These are Portugal's most popular payment methods:

- **Multibanco**: ATM and online banking payments using a payment
  reference
- **MB WAY**: Mobile payment solution with push notifications

### How Multibanco Works

1.  **Payment Request**: Customer initiates payment on website
2.  **Reference Generation**: EasyPay API generates a payment reference
3.  **Reference Display**: Customer receives Entity, Reference, and
    Amount
4.  **Customer Payment**: Customer pays at ATM/online banking/MB WAY
5.  **Webhook Notification**: EasyPay notifies Odoo of payment
    confirmation
6.  **Order Confirmation**: Order is automatically confirmed

### How MB WAY Works

1.  **Payment Request**: Customer initiates payment and enters phone
    number
2.  **Push Notification**: EasyPay sends push notification to MB WAY app
3.  **Customer Approval**: Customer opens app and approves payment with
    PIN
4.  **Instant Confirmation**: Payment confirmed immediately
5.  **Webhook Notification**: EasyPay notifies Odoo
6.  **Order Confirmation**: Order is automatically confirmed

### Implementation Details

#### Models

##### payment.transaction (Extended)

**Multibanco Fields:**

- `easypay_mb_entity` - Multibanco entity number (e.g., "12345")
- `easypay_mb_reference` - Multibanco reference number (e.g., "123 456
  789")
- `easypay_mb_expiry_date` - Reference expiry date

**MB WAY Fields:**

- `easypay_mbway_phone` - Customer's phone number
- `easypay_mbway_alias` - MB WAY alias from EasyPay
- `easypay_mbway_status` - Payment request status
  (pending/waiting/approved/declined/timeout)

**Methods:**

- `_get_specific_processing_values()` - Extracts Multibanco/MB WAY data
  from API response
- `_easypay_get_payment_details()` - Fetches payment details from
  EasyPay API

#### API Integration

##### EasyPay API Endpoint

**Create Single Payment:**

``` 
POST /2.0/single
```

**Request Payload:**

``` json
{
    "type": "sale",
    "method": "mb",
    "value": 100.00,
    "currency": "EUR",
    "key": "ORDER-001",
    "customer": {
        "name": "Customer Name",
        "email": "customer@example.com"
    }
}
```

**Response:**

``` json
{
    "id": "payment-uuid",
    "method": {
        "type": "mb",
        "entity": "12345",
        "reference": "123 456 789",
        "expiration_date": "2025-10-15T23:59:59Z",
        "url": null
    },
    "status": "pending"
}
```

##### MB WAY Payment Request

**Request Payload:**

``` json
{
    "type": "sale",
    "method": "mbw",
    "value": 100.00,
    "currency": "EUR",
    "key": "ORDER-001",
    "customer": {
        "name": "Customer Name",
        "email": "customer@example.com",
        "phone": "+351912345678"
    }
}
```

**Response:**

``` json
{
    "id": "payment-uuid",
    "method": {
        "type": "mbw",
        "alias": "912345678",
        "status": "waiting",
        "url": null
    },
    "status": "pending"
}
```

**Status Values:**

- `pending` - Request created
- `waiting` - Waiting for customer approval
- `approved` - Customer approved payment
- `declined` - Customer declined payment
- `timeout` - Request expired (4 minutes)

##### Get Payment Details

**Endpoint:**

``` 
GET /2.0/single/{payment_id}
```

**Response:** Same as create response with current status

#### Views

##### Frontend Template: multibanco_reference

Displays the payment reference to customers with:

- Entity number
- Reference number
- Amount
- Expiry date
- Payment instructions

##### Backend View: payment_transaction_form_mb

Adds Multibanco fields to transaction form view for admin visibility.

#### Workflow

``` 
Customer Checkout
       ↓
_get_specific_processing_values()
       ↓
EasyPay API: POST /2.0/single (method=mb)
       ↓
Extract: entity, reference, expiry_date
       ↓
Display Multibanco Reference Template
       ↓
Customer Pays at ATM/Banking
       ↓
EasyPay Webhook: Payment Confirmed
       ↓
_handle_notification_data()
       ↓
Transaction State: done
       ↓
Order Confirmed
```

### Testing

#### Test Multibanco Payment

1.  Create a sale order
2.  Select EasyPay payment provider with method="mb"
3.  Proceed to payment
4.  Verify reference is displayed
5.  Use EasyPay test environment to simulate payment
6.  Verify webhook updates transaction status

#### Test Data (EasyPay Sandbox)

- Test Entity: Provided by EasyPay
- Test Reference: Auto-generated
- Test Amount: Any amount
- Payment Simulation: Available in EasyPay dashboard

### Security Considerations

- References are unique per transaction
- Expiry dates prevent old references from being used
- Webhook validation ensures payment authenticity
- No sensitive data stored (references are public)

### Performance

- Reference generation: ~500ms (API call)
- Payment confirmation: Real-time via webhook
- No polling required

### Limitations

- Multibanco payments are not instant (can take minutes)
- References expire after configured period
- Only works for EUR currency
- Only available in Portugal

### Future Enhancements

- QR code generation for mobile payments
- Email notification with reference
- SMS notification option
- Reference regeneration if expired
- Printable reference voucher
