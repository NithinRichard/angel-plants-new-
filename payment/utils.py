import razorpay
import logging
import os
import json
import uuid
from functools import lru_cache
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ImproperlyConfigured

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Razorpay client as None
client = None

def get_razorpay_client():
    """Initialize and return the Razorpay client with proper error handling"""
    global client
    
    if client is not None:
        return client
        
    logger.info("Initializing Razorpay client...")
    
    # Get keys from Django settings
    razorpay_key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
    razorpay_key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
    
    # Debug logging
    key_id_display = f"{razorpay_key_id[:8]}..." if razorpay_key_id and len(razorpay_key_id) > 8 else str(razorpay_key_id)
    logger.debug(f"RAZORPAY_KEY_ID from settings: {key_id_display}")
    
    # Validate keys
    if not razorpay_key_id or not razorpay_key_secret:
        error_msg = "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set in settings"
        logger.critical(error_msg)
        raise ImproperlyConfigured(error_msg)
        
    if not isinstance(razorpay_key_id, str) or not razorpay_key_id.strip():
        error_msg = "RAZORPAY_KEY_ID is empty or not a valid string"
        logger.critical(error_msg)
        raise ImproperlyConfigured(error_msg)
        
    if not isinstance(razorpay_key_secret, str) or not razorpay_key_secret.strip():
        error_msg = "RAZORPAY_KEY_SECRET is empty or not a valid string"
        logger.critical(error_msg)
        raise ImproperlyConfigured(error_msg)
    
    logger.debug(f"Using Razorpay Key ID: {razorpay_key_id[:8]}...")
    
    try:
        client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))
        logger.info("Successfully initialized Razorpay client")
        
        # Test the connection by fetching account details
        try:
            account = client.account.fetch()
            logger.debug(f"Razorpay account details: {account}")
        except Exception as e:
            logger.warning(f"Could not fetch Razorpay account details: {str(e)}")
            
        logger.info("Razorpay client initialization complete")
        return client
        
    except Exception as e:
        error_msg = f"Failed to initialize Razorpay client: {str(e)}"
        logger.critical(error_msg)
        raise ImproperlyConfigured(error_msg)

# Initialize the client when the module loads
try:
    client = get_razorpay_client()
except ImproperlyConfigured as e:
    logger.error(f"Failed to initialize Razorpay client: {str(e)}")
    # Don't raise here, let it fail when actually trying to use the client
    
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
    try:
        client = get_razorpay_client()
        
        if not isinstance(amount, int) or amount <= 0:
            raise ValueError("Amount must be a positive integer")
            
        if not isinstance(currency, str) or not currency.strip():
            raise ValueError("Currency must be a non-empty string")
            
        if receipt is None:
            receipt = f"order_{uuid.uuid4().hex}"
            
        if notes is None:
            notes = {}
        
        logger.info(f"Creating Razorpay order for amount: {amount} {currency}")
        
        order_data = {
            'amount': amount,
            'currency': currency,
            'receipt': receipt,
            'notes': notes,
            'payment_capture': 1  # Auto-capture payment
        }
        
        logger.debug(f"Order data: {order_data}")
        
        # Create order
        order = client.order.create(data=order_data)
        logger.info(f"Created Razorpay order: {order.get('id')}")
        
        return order
        
    except Exception as e:
        error_msg = f"Failed to create Razorpay order: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg)

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
    try:
        client = get_razorpay_client()
        
        if isinstance(payload, dict):
            payload = json.dumps(payload)
            
        client.utility.verify_webhook_signature(payload, signature, secret)
        return True
        
    except Exception as e:
        logger.error(f"Signature verification failed: {str(e)}")
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
    try:
        client = get_razorpay_client()
        
        if not payment_id or not isinstance(payment_id, str):
            raise ValueError("Invalid payment_id")
            
        if not isinstance(amount, int) or amount <= 0:
            raise ValueError("Amount must be a positive integer")
        
        logger.info(f"Capturing payment {payment_id} for amount: {amount}")
        
        # Capture the payment
        capture = client.payment.capture(payment_id, amount)
        logger.info(f"Successfully captured payment {payment_id}")
        return capture
        
    except Exception as e:
        error_msg = f"Failed to capture payment {payment_id}: {str(e)}"
        logger.error(error_msg)
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
    try:
        client = get_razorpay_client()
        
        if not payment_id or not isinstance(payment_id, str):
            raise ValueError("Invalid payment_id")
        
        logger.info(f"Fetching payment details for {payment_id}")
        
        payment = client.payment.fetch(payment_id)
        logger.debug(f"Payment details for {payment_id}: {payment}")
        return payment
        
    except Exception as e:
        error_msg = f"Error fetching payment details for {payment_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e
