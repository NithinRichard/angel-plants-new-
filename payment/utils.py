import razorpay
import logging
import os
import json
import uuid
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ImproperlyConfigured

# Set up logging
logger = logging.getLogger(__name__)


# Validate Razorpay settings
if not all([hasattr(settings, 'RAZORPAY_KEY_ID'), hasattr(settings, 'RAZORPAY_KEY_SECRET')]):
    error_msg = "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set in settings"
    logger.critical(error_msg)
    raise ImproperlyConfigured(error_msg)

# Initialize Razorpay client
client = None

try:
    logger.info("Initializing Razorpay client...")
    # Get keys from Django settings
    razorpay_key_id = getattr(settings, 'RAZORPAY_KEY_ID', None)
    razorpay_key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', None)
    
    # Debug logging
    logger.debug(f"RAZORPAY_KEY_ID from settings: {razorpay_key_id[:8] if razorpay_key_id else 'NOT FOUND'}")
    
    if not razorpay_key_id or not razorpay_key_secret:
        error_msg = "Razorpay API keys are not properly configured in settings.py"
        logger.critical(error_msg)
        raise ImproperlyConfigured(error_msg)
    
    logger.debug(f"Using Razorpay Key ID: {razorpay_key_id[:8]}...")
    
    client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))
    logger.info("Successfully initialized Razorpay client")
    
    # Test the connection by fetching account details
    try:
        account = client.account.fetch()
        logger.debug(f"Razorpay account details: {account}")
    except Exception as e:
        logger.warning(f"Could not fetch Razorpay account details: {str(e)}")
    
    logger.info("Razorpay client initialization complete")
    
except Exception as e:
    error_msg = f"Failed to initialize Razorpay client: {str(e)}"
    logger.critical(error_msg, exc_info=True)
    raise

def create_razorpay_order(amount, currency='INR', receipt=None, notes=None):
    """
    Create a Razorpay order using the global client
    
    Args:
        amount (int): Amount in paise (e.g., 100 = ₹1.00)
        currency (str): Currency code (default: 'INR')
        receipt (str, optional): Order receipt ID. If not provided, a random one will be generated.
        notes (dict, optional): Additional notes to store with the order
        
    Returns:
        dict: Razorpay order details
        
    Raises:
        ValueError: If amount or currency is invalid
        Exception: For Razorpay API errors or if client is not initialized
    """
    global client
    
    logger.info(f"Creating Razorpay order - Amount: {amount} {currency}, Receipt: {receipt}")
    
    # Check if client is initialized
    if not client:
        error_msg = "Razorpay client not initialized"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    # Validate amount
    if not isinstance(amount, int) or amount <= 0:
        error_msg = f"Invalid amount: {amount}. Amount must be a positive integer in paise."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Validate currency
    if not isinstance(currency, str) or len(currency) != 3:
        error_msg = f"Invalid currency: {currency}. Must be a 3-letter currency code."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Create order data
        order_data = {
            'amount': amount,  # amount in the smallest currency unit (paise for INR)
            'currency': currency.upper(),
            'payment_capture': '1',  # auto-capture payment
            'receipt': receipt or f"rcpt_{uuid.uuid4().hex[:12]}",
        }
        
        if notes and isinstance(notes, dict):
            order_data['notes'] = notes
        
        logger.debug(f"Creating Razorpay order with data: {json.dumps(order_data, indent=2)}")
        
        # Create order
        order = client.order.create(data=order_data)
        
        if order and 'id' in order:
            logger.info(f"Successfully created Razorpay order: {order['id']}")
            logger.debug(f"Order details: {json.dumps(order, indent=2)}")
            return order
        else:
            error_msg = f"Failed to create order. Invalid response: {order}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
    except razorpay.errors.BadRequestError as e:
        error_msg = f"Bad request while creating Razorpay order: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e
    except razorpay.errors.ServerError as e:
        error_msg = f"Razorpay server error while creating order: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e
    except razorpay.errors.UnauthorizedError as e:
        error_msg = "Authentication failed. Please check Razorpay API keys."
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error creating Razorpay order: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e

def verify_payment_signature(payload, signature, secret):
    """
    Verify the webhook signature
    
    Args:
        payload (dict or str): The webhook payload
        signature (str): The X-Razorpay-Signature header
        secret (str): The webhook secret from Razorpay
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not all([payload, signature, secret]):
        logger.warning("Missing required parameters for signature verification")
        return False
    
    try:
        if isinstance(payload, dict):
            payload = json.dumps(payload, separators=(',', ':'))
            
        client.utility.verify_webhook_signature(payload, signature, secret)
        logger.debug("Successfully verified webhook signature")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {str(e)}")
        return False

def capture_payment(payment_id, amount):
    """
    Capture a payment
    
    Args:
        payment_id (str): Razorpay payment ID
        amount (int): Amount in paise to capture
        
    Returns:
        dict: Capture response from Razorpay or None if failed
        
    Raises:
        ValueError: If payment_id or amount is invalid
        Exception: For Razorpay API errors
    """
    if not payment_id:
        error_msg = "Payment ID is required"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    if not isinstance(amount, int) or amount <= 0:
        error_msg = f"Invalid amount: {amount}. Amount must be a positive integer in paise."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        logger.info(f"Capturing payment {payment_id} for amount {amount} paise")
        capture_data = client.payment.capture(payment_id, amount)
        logger.info(f"Successfully captured payment {payment_id}")
        return capture_data
        
    except razorpay.errors.BadRequestError as e:
        error_msg = f"Bad request while capturing payment {payment_id}: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg) from e
    except razorpay.errors.ServerError as e:
        error_msg = f"Server error while capturing payment {payment_id}: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error capturing payment {payment_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e

def get_payment_details(payment_id):
    """
    Get payment details from Razorpay
    
    Args:
        payment_id (str): Razorpay payment ID
        
    Returns:
        dict: Payment details from Razorpay
        
    Raises:
        ValueError: If payment_id is invalid
        Exception: For Razorpay API errors
    """
    if not payment_id:
        error_msg = "Payment ID is required"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        logger.debug(f"Fetching payment details for {payment_id}")
        payment = client.payment.fetch(payment_id)
        logger.debug(f"Retrieved payment details for {payment_id}")
        return payment
        
    except razorpay.errors.NotFoundError as e:
        error_msg = f"Payment not found: {payment_id}"
        logger.error(error_msg)
        raise Exception(error_msg) from e
    except razorpay.errors.BadRequestError as e:
        error_msg = f"Invalid payment ID: {payment_id}"
        logger.error(error_msg)
        raise ValueError(error_msg) from e
    except Exception as e:
        error_msg = f"Error fetching payment details for {payment_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e
