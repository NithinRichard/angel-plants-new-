import configparser
from pathlib import Path

# Load configuration
BASE_DIR = Path(__file__).resolve().parent
config_path = BASE_DIR / 'config.ini'
print(f"Loading configuration from: {config_path}")

config = configparser.ConfigParser()
config.read(config_path)

# Print configuration
print("\n=== Configuration ===")
print(f"Database: {config.get('Database', 'NAME', fallback='NOT FOUND')}")
print(f"Database User: {config.get('Database', 'USER', fallback='NOT FOUND')}")
print(f"Razorpay Key ID: {config.get('Razorpay', 'KEY_ID', fallback='NOT FOUND')}")
razorpay_secret = config.get('Razorpay', 'KEY_SECRET', fallback=None)
print(f"Razorpay Key Secret: {'*' * 8 + (razorpay_secret[-4:] if razorpay_secret else '') if razorpay_secret else 'NOT FOUND'}")
print("====================")
