import razorpay
import json
import logging
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from decimal import Decimal
from hashlib import sha256
import hmac
import base64

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Razorpay client
client = None
if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
    try:
        logger.info("Initializing Razorpay client")
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        logger.info("Razorpay client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Razorpay client: {str(e)}")
        client = None
else:
    logger.warning(
        'Razorpay is not configured. Payment functionality will be disabled. '
        'Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET environment variables to enable payments.'
    )

def create_razorpay_order(amount, currency='INR', receipt=None, notes=None):
    """
    Create a Razorpay order
    
    Args:
        amount (Decimal or str): Order amount in INR
        currency (str, optional): Currency code. Defaults to 'INR'.
        receipt (str, optional): Receipt ID. If not provided, a random one will be generated.
        notes (dict, optional): Additional notes to be added to the order.
        
    Returns:
        dict: Razorpay order details or None if failed or Razorpay is not configured
    """
    if client is None:
        logger.warning("Razorpay is not configured. Cannot create order.")
        return None
        
    try:
        # Validate input
        if not amount or (isinstance(amount, (str, int, float)) and float(amount) <= 0):
            logger.error(f"Invalid amount: {amount}")
            return None
            
        # Convert amount to paise (smallest currency unit for INR)
        try:
            amount_decimal = Decimal(str(amount))
            amount_in_paise = int(amount_decimal * 100)
            
            # Validate amount
            if amount_in_paise < 100:  # Minimum amount for Razorpay is 1 INR (100 paise)
                logger.error(f"Amount too low: {amount_in_paise} paise")
                return None
                
            if amount_in_paise > 50000000:  # 500,000 INR maximum
                logger.error(f"Amount too high: {amount_in_paise} paise")
                return None
                
        except (ValueError, TypeError, decimal.InvalidOperation) as e:
            logger.error(f"Invalid amount format: {amount}, error: {str(e)}")
            return None
            
        # Prepare order data
        order_data = {
            'amount': amount_in_paise,
            'currency': currency.upper(),
            'payment_capture': 1,  # Auto capture payment
            'notes': notes or {}
        }
        
        # Add receipt if provided
        if receipt:
            order_data['receipt'] = str(receipt)[:40]  # Max 40 chars for receipt ID
        # Add timestamp to notes if not provided
        if 'timestamp' not in order_data['notes']:
            order_data['notes']['timestamp'] = timezone.now().isoformat()
            
        logger.info(f"Creating Razorpay order with data: {order_data}")
        
        # Create the order
        order = client.order.create(data=order_data)
        logger.info(f"Created Razorpay order: {order['id']}")
        
        return order
        
    except razorpay.errors.BadRequestError as e:
        logger.error(f"Bad request to Razorpay API: {str(e)}")
        logger.error(f"Error details: {e.error}")
        return None
    except Exception as e:
        logger.exception("Error creating Razorpay order")
        return None

def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    """
    Verify the payment signature from Razorpay
    
    Args:
        razorpay_order_id (str): The Razorpay order ID
        razorpay_payment_id (str): The Razorpay payment ID
        razorpay_signature (str): The signature to verify
        
    Returns:
        bool: True if signature is valid, False otherwise or if Razorpay is not configured
    """
    if client is None or not settings.RAZORPAY_KEY_SECRET:
        logger.warning("Razorpay is not configured. Cannot verify payment signature.")
        return False
        
    try:
        logger.info(f"Verifying payment signature for order: {razorpay_order_id}")
        
        # Create the payload in the format expected by Razorpay
        payload = f"{razorpay_order_id}|{razorpay_payment_id}"
        
        # Verify the signature
        generated_signature = hmac.new(
            key=settings.RAZORPAY_KEY_SECRET.encode('utf-8'),
            msg=payload.encode('utf-8'),
            digestmod=sha256
        ).hexdigest()
        
        # Compare the generated signature with the one provided
        is_valid = hmac.compare_digest(generated_signature, razorpay_signature)
        
        if is_valid:
            logger.info(f"Payment signature verified for order: {razorpay_order_id}")
        else:
            logger.warning(f"Invalid payment signature for order: {razorpay_order_id}")
            
        return is_valid
        
    except Exception as e:
        logger.error(f"Error verifying payment signature: {str(e)}", exc_info=True)
        return False

def verify_webhook_signature(payload, signature, webhook_secret=None):
    """
    Verify the webhook signature from Razorpay
    
    Args:
        payload (str): The raw request body as a string
        signature (str): The X-Razorpay-Signature header
        webhook_secret (str, optional): The webhook secret. If not provided, uses settings.RAZORPAY_WEBHOOK_SECRET
        
    Returns:
        bool: True if signature is valid, False otherwise or if Razorpay is not configured
    """
    if client is None:
        logger.warning("Razorpay is not configured. Cannot verify webhook signature.")
        return False
        
    try:
        if not webhook_secret:
            webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
            
        if not webhook_secret:
            logger.error("Webhook secret not configured")
            return False
            
        # Create HMAC SHA256 hash
        key = webhook_secret.encode('utf-8')
        msg = payload.encode('utf-8')
        
        expected_signature = hmac.new(key, msg, sha256).hexdigest()
        
        # Compare the signatures in constant time to prevent timing attacks
        is_valid = hmac.compare_digest(expected_signature, signature)
        
        if not is_valid:
            logger.warning("Webhook signature verification failed")
            
        return is_valid
        
    except Exception as e:
        logger.exception("Error in verify_webhook_signature")
        return False


def get_payment_status(payment_id):
    """
    Get the status of a payment from Razorpay
    
    Args:
        payment_id (str): The Razorpay payment ID
        
    Returns:
        dict: Payment details or None if failed or Razorpay is not configured
    """
    if client is None:
        logger.warning("Razorpay is not configured. Cannot fetch payment status.")
        return None
        
    try:
        if not payment_id:
            logger.error("No payment ID provided")
            return None
            
        payment = client.payment.fetch(payment_id)
        logger.debug(f"Fetched payment status: {payment}")
        return payment
        
    except razorpay.errors.BadRequestError as e:
        logger.error(f"Bad request to Razorpay API: {str(e)}")
        return None
    except Exception as e:
        logger.exception("Error getting payment status")
        return None
