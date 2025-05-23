"""
Tests for payment utility functions.
"""
import json
import uuid
from unittest.mock import patch, MagicMock

import pytest
from django.test import TestCase, override_settings
from django.utils import timezone

from payment.utils import (
    create_razorpay_order,
    verify_payment_signature,
    capture_payment,
    get_payment_details,
)


class TestRazorpayUtils(TestCase):
    """Test Razorpay utility functions."""

    def setUp(self):
        """Set up test data."""
        self.amount = 10000  # 100.00 INR
        self.currency = 'INR'
        self.receipt = f"test_rcpt_{uuid.uuid4().hex[:8]}"
        self.payment_id = 'pay_test1234567890'
        self.order_id = 'order_test1234567890'
        self.signature = 'test_signature_1234567890'

    @patch('payment.utils.client.order.create')
    def test_create_razorpay_order_success(self, mock_create):
        """Test creating a Razorpay order successfully."""
        # Mock the Razorpay client response
        expected_response = {
            'id': self.order_id,
            'amount': self.amount,
            'currency': self.currency,
            'status': 'created',
            'receipt': self.receipt,
        }
        mock_create.return_value = expected_response

        # Call the function
        result = create_razorpay_order(
            amount=self.amount,
            currency=self.currency,
            receipt=self.receipt,
            notes={'key': 'value'}
        )

        # Assertions
        self.assertEqual(result, expected_response)
        mock_create.assert_called_once_with(data={
            'amount': self.amount,
            'currency': self.currency,
            'receipt': self.receipt,
            'payment_capture': '1',
            'notes': {'key': 'value'}
        })

    def test_create_razorpay_order_invalid_amount(self):
        """Test creating a Razorpay order with invalid amount."""
        with self.assertRaises(ValueError) as context:
            create_razorpay_order(amount=0)
        self.assertIn('Amount must be a positive integer', str(context.exception))

    @patch('payment.utils.client.utility.verify_webhook_signature')
    def test_verify_payment_signature_success(self, mock_verify):
        """Test verifying a payment signature successfully."""
        # Mock the verification
        mock_verify.return_value = True
        
        # Test data
        payload = {'order_id': self.order_id, 'payment_id': self.payment_id}
        secret = 'test_webhook_secret'
        
        # Call the function
        result = verify_payment_signature(
            payload=payload,
            signature=self.signature,
            secret=secret
        )
        
        # Assertions
        self.assertTrue(result)
        mock_verify.assert_called_once()

    @patch('payment.utils.client.payment.capture')
    def test_capture_payment_success(self, mock_capture):
        """Test capturing a payment successfully."""
        # Mock the capture response
        mock_response = {
            'id': self.payment_id,
            'amount': self.amount,
            'currency': self.currency,
            'status': 'captured'
        }
        mock_capture.return_value = mock_response

        # Call the function
        result = capture_payment(
            payment_id=self.payment_id,
            amount=self.amount
        )

        # Assertions
        self.assertEqual(result, mock_response)
        mock_capture.assert_called_once_with(self.payment_id, self.amount)

    @patch('payment.utils.client.payment.fetch')
    def test_get_payment_details_success(self, mock_fetch):
        """Test getting payment details successfully."""
        # Mock the fetch response
        mock_response = {
            'id': self.payment_id,
            'amount': self.amount,
            'currency': self.currency,
            'status': 'captured',
            'order_id': self.order_id
        }
        mock_fetch.return_value = mock_response

        # Call the function
        result = get_payment_details(payment_id=self.payment_id)

        # Assertions
        self.assertEqual(result, mock_response)
        mock_fetch.assert_called_once_with(self.payment_id)

    def test_verify_payment_signature_missing_params(self):
        """Test verifying signature with missing parameters."""
        # Test with missing payload
        self.assertFalse(verify_payment_signature(
            payload=None,
            signature=self.signature,
            secret='test_secret'
        ))
        
        # Test with missing signature
        self.assertFalse(verify_payment_signature(
            payload={'key': 'value'},
            signature=None,
            secret='test_secret'
        ))
        
        # Test with missing secret
        self.assertFalse(verify_payment_signature(
            payload={'key': 'value'},
            signature=self.signature,
            secret=None
        ))

    @patch('payment.utils.client.payment.capture')
    def test_capture_payment_invalid_amount(self, mock_capture):
        """Test capturing a payment with invalid amount."""
        with self.assertRaises(ValueError) as context:
            capture_payment(payment_id=self.payment_id, amount=0)
        self.assertIn('Amount must be a positive integer', str(context.exception))
        mock_capture.assert_not_called()

    def test_get_payment_details_invalid_id(self):
        """Test getting payment details with invalid payment ID."""
        with self.assertRaises(ValueError):
            get_payment_details(payment_id='')


if __name__ == '__main__':
    import unittest
    unittest.main()
