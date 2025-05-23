import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / '.env'
print(f"Loading .env file from: {env_path}")
load_dotenv(env_path)

# Print environment variables
print("\n=== Environment Variables ===")
print(f"RAZORPAY_KEY_ID: {os.getenv('RAZORPAY_KEY_ID', 'NOT FOUND')}")
print(f"RAZORPAY_KEY_SECRET: {'*' * 8 + os.getenv('RAZORPAY_KEY_SECRET', 'NOT FOUND')[-4:] if os.getenv('RAZORPAY_KEY_SECRET') else 'NOT FOUND'}")
print("===========================")
