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
try:
    logger.info(f"Initializing Razorpay client with key: {settings.RAZORPAY_KEY_ID}")
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    logger.info("Razorpay client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Razorpay client: {str(e)}")
    raise

def create_razorpay_order(amount, currency='INR', receipt=None, notes=None):
    """
    Create a Razorpay order
    
    Args:
        amount (Decimal): Order amount in INR
        currency (str, optional): Currency code. Defaults to 'INR'.
        receipt (str, optional): Receipt ID. If not provided, a random one will be generated.
        notes (dict, optional): Additional notes to be added to the order.
        
    Returns:
        dict: Razorpay order details or None if failed
    """
    try:
        # Convert amount to paise (smallest currency unit for INR)
        amount_in_paise = int(Decimal(str(amount)) * 100)
        
        if amount_in_paise < 100:  # Minimum amount for Razorpay is 1 INR (100 paise)
            logger.error(f"Amount too low: {amount_in_paise} paise")
            return None
            
        # Prepare order data
        order_data = {
            'amount': amount_in_paise,
            'currency': currency,
            'payment_capture': 1,  # Auto capture payment
            'notes': notes or {}
        }
        
        # Add receipt if provided
        if receipt:
            order_data['receipt'] = receipt
            
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
        bool: True if signature is valid, False otherwise
    """
    try:
        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            logger.error("Missing required parameters for signature verification")
            return False
            
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        logger.debug(f"Verifying payment signature with params: {params_dict}")
        is_valid = client.utility.verify_payment_signature(params_dict)
        
        if not is_valid:
            logger.warning(f"Invalid signature for order {razorpay_order_id}")
            
        return is_valid
        
    except razorpay.errors.SignatureVerificationError as e:
        logger.error(f"Signature verification failed: {str(e)}")
        return False
    except Exception as e:
        logger.exception("Error in verify_payment_signature")
        return False


def verify_webhook_signature(payload, signature, webhook_secret=None):
    """
    Verify the webhook signature from Razorpay
    
    Args:
        payload (str): The raw request body as a string
        signature (str): The X-Razorpay-Signature header
        webhook_secret (str, optional): The webhook secret. If not provided, uses settings.RAZORPAY_WEBHOOK_SECRET
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
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
        return hmac.compare_digest(expected_signature, signature)
        
    except Exception as e:
        logger.exception("Error in verify_webhook_signature")
        return False


def get_payment_status(payment_id):
    """
    Get the status of a payment from Razorpay
    
    Args:
        payment_id (str): The Razorpay payment ID
        
    Returns:
        dict: Payment details or None if failed
    """
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
