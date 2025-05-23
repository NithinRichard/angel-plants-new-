"""
Simple test file to verify test database setup.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class SimpleTest(TestCase):
    """Simple test case to verify test database setup."""
    
    def test_database_setup(self):
        """Test that the test database is set up correctly."""
        # Create a test user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Verify the user was created
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.username, 'testuser')
