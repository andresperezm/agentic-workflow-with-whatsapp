
import firebase_admin
from firebase_admin import credentials, firestore
from faker import Faker
import random
import sys
import datetime

# Initialize Firebase Admin SDK
# Use Application Default Credentials
if not firebase_admin._apps:
    firebase_admin.initialize_app()

db = firestore.client()

# Initialize Faker with Mexico locale
fake = Faker('es_MX')

def generate_mock_users(num_users):
    users_ref = db.collection('users')

    print("--- Starting User Generation ---")
    print(f"Count: {num_users} users")
    print("---------------------------\n")

    for i in range(num_users):
        phone_number = fake.phone_number()
        user_email = fake.email()
        user_name = fake.name()
        
        # Ensure unique phone number (basic check not needed for mock data usually, but good practice)
        # For simplicity in mock generation, we trust Faker's randomness or just proceed.

        user_data = {
            'phoneNumber': phone_number,
            'userEmail': user_email,
            'userName': user_name,
            'createdAt': datetime.datetime.now()
        }

        try:
            # Add to Firestore
            users_ref.add(user_data)
            print(f"[{i + 1}/{num_users}] ✅ Created user: {user_name} ({phone_number})")
        except Exception as e:
            print(f"❌ Error inserting user {i}: {e}")

    print("\n✨ All users have been successfully inserted.")

if __name__ == "__main__":
    # Usage: python test_users.py <numUsers>
    args = sys.argv[1:]
    
    # Defaults
    num_users = 5

    if len(args) >= 1:
        try:
            num_users = int(args[0])
        except ValueError:
            pass
    
    generate_mock_users(num_users)
