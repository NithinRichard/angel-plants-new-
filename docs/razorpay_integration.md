# Razorpay Payment Integration

This document provides an overview of the Razorpay payment integration in the Angel Plants e-commerce platform.

## Setup Instructions

### 1. Environment Variables

Create a `.env` file in the project root and add the following variables:

```bash
# Copy .env.example to .env and update the values
cp .env.example .env
```

Update the following Razorpay-related variables in your `.env` file:

```
# Razorpay Configuration
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
WEBHOOK_BASE_URL=http://yourdomain.com
```

### 2. Razorpay Dashboard Setup

1. Sign up for a Razorpay account at https://razorpay.com/
2. Go to the Razorpay Dashboard: https://dashboard.razorpay.com/
3. Navigate to Settings → API Keys
4. Generate new API keys (or use existing ones)
5. Update the `.env` file with your API keys

### 3. Webhook Configuration (Recommended for Production)

1. In Razorpay Dashboard, go to Settings → Webhooks
2. Add a new webhook with the following details:
   - URL: `https://yourdomain.com/payment/webhook/`
   - Active Events:
     - `payment.captured`
     - `payment.failed`
     - `order.paid`
3. Copy the webhook secret and update the `RAZORPAY_WEBHOOK_SECRET` in your `.env` file

## Payment Flow

1. **Order Creation**:
   - User selects products and proceeds to checkout
   - System creates an order in the database with status 'Pending'
   - User selects Razorpay as the payment method

2. **Payment Initialization**:
   - Frontend calls the `create_order` endpoint to get Razorpay order details
   - Razorpay checkout form is displayed to the user

3. **Payment Processing**:
   - User completes the payment on Razorpay's secure payment page
   - Razorpay redirects to the success/failure URL based on payment status

4. **Webhook Handling (Async)**:
   - Razorpay sends a webhook notification to our server
   - System verifies the webhook signature
   - Order status is updated based on the payment status

## API Endpoints

- `POST /payment/create_order/` - Create a new Razorpay order
- `POST /payment/webhook/` - Handle Razorpay webhook notifications
- `GET /payment/success/` - Payment success page
- `GET /payment/failed/` - Payment failure page

## Testing

### Test Cards

Use the following test cards in Razorpay's test mode:

- **Success**: `4111 1111 1111 1111` (any future date and CVV)
- **Failure**: `4111 1111 1111 1112` (any future date and CVV)
- **Authentication Required**: `4012 0000 3338 5509` (any future date and CVV)

### Test Webhooks

You can use Razorpay's webhook testing tool or the following cURL command:

```bash
curl -X POST https://yourdomain.com/payment/webhook/ \
  -H "Content-Type: application/json" \
  -H "X-Razorpay-Signature: your_webhook_signature" \
  -d '{
    "event": "payment.captured",
    "payload": {
      "payment": {
        "entity": {
          "id": "pay_1234567890",
          "amount": 10000,
          "currency": "INR",
          "status": "captured",
          "order_id": "order_1234567890",
          "invoice_id": null,
          "international": false,
          "method": "card",
          "amount_refunded": 0,
          "refund_status": null,
          "captured": true,
          "email": "test@example.com",
          "contact": "+919999999999"
        }
      }
    }
  }'
```

## Error Handling

Common errors and their resolutions:

1. **Invalid API Key**: Verify your Razorpay API keys in settings
2. **Webhook Verification Failed**: Check the webhook secret and signature
3. **Order Not Found**: Ensure the order exists in your database
4. **Payment Capture Failed**: Check the payment status in Razorpay dashboard

## Security Considerations

1. Never commit your Razorpay API keys to version control
2. Use environment variables for sensitive information
3. Verify webhook signatures to ensure requests are from Razorpay
4. Use HTTPS in production to secure payment data in transit
5. Regularly rotate your API keys and webhook secrets

## Monitoring

Check the following logs for troubleshooting:

- `logs/razorpay.log` - Payment-related logs
- `logs/django_errors.log` - Application errors

## Support

For issues with the Razorpay integration, contact:

- Razorpay Support: https://razorpay.com/support/
- Developer Documentation: https://razorpay.com/docs/
