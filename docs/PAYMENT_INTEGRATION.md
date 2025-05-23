# Payment Integration with Razorpay

This document provides a guide on how to set up and use the Razorpay payment gateway in the Angel's Plants e-commerce application.

## Prerequisites

1. Razorpay account - Sign up at [Razorpay](https://dashboard.razorpay.com/signup)
2. API keys from Razorpay Dashboard
3. Python 3.8+
4. Django 4.0+
5. `razorpay` Python package

## Setup Instructions

### 1. Environment Variables

Create a `.env` file in the project root and add the following variables:

```bash
# Razorpay Configuration
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

### 2. Install Dependencies

```bash
pip install razorpay python-dotenv
```

### 3. Webhook Setup

1. Go to Razorpay Dashboard → Webhooks
2. Add a new webhook with the following URL:
   ```
   https://yourdomain.com/payment/webhook/
   ```
3. Select the following events to listen for:
   - `payment.captured`
   - `payment.failed`
   - `order.paid`
4. Save the webhook secret and update it in your `.env` file

### 4. Testing in Development

For testing, you can use Razorpay's test mode:

1. Use test API keys from Razorpay Dashboard
2. Use the following test card details:
   - Card Number: `4111 1111 1111 1111`
   - Expiry: Any future date
   - CVV: Any 3 digits
   - Name: Any name

## Payment Flow

1. **Order Creation**:
   - User adds items to cart and proceeds to checkout
   - System creates an order in the database with status 'pending'

2. **Payment Initialization**:
   - User is redirected to the payment page
   - System creates a Razorpay order
   - Payment form is displayed with Razorpay checkout

3. **Payment Processing**:
   - User enters payment details
   - Razorpay processes the payment
   - On success, user is redirected to success page
   - On failure, user is shown an error message

4. **Webhook Handling**:
   - Razorpay sends a webhook notification
   - System verifies the webhook signature
   - Order status is updated based on payment status

## API Endpoints

- `POST /checkout/payment/<int:order_id>/`: Payment page
- `POST /checkout/payment/create-order/`: Create Razorpay order (AJAX)
- `GET /checkout/payment/success/`: Payment success page
- `GET /checkout/payment/failed/`: Payment failed page
- `POST /payment/webhook/`: Razorpay webhook handler

## Error Handling

Common errors and solutions:

1. **Invalid Signature**
   - Verify your webhook secret
   - Ensure the payload is not modified

2. **Payment Failed**
   - Check Razorpay dashboard for failure reason
   - Verify user has sufficient funds

3. **Webhook Notifications**
   - Check webhook logs in Razorpay dashboard
   - Ensure your server is accessible from the internet

## Security Considerations

1. Never commit your API keys to version control
2. Always verify webhook signatures
3. Use HTTPS in production
4. Implement rate limiting on payment endpoints
5. Log all payment-related activities

## Testing

To test the payment flow:

1. Add items to cart
2. Proceed to checkout
3. Select 'Pay with Razorpay'
4. Use test card details
5. Verify order status updates correctly

## Support

For any issues, please contact support@angelsplants.com
