
import firebase_admin
from firebase_admin import credentials, firestore
from faker import Faker
import random
import uuid
import sys
import datetime

# Initialize Firebase Admin SDK
# Use Application Default Credentials
if not firebase_admin._apps:
    firebase_admin.initialize_app()

db = firestore.client()

# Initialize Faker with Mexico locale
fake = Faker('es_MX')

# Status options
STATUS_OPTIONS = ['creada', 'procesando', 'enviada', 'entregada', 'cancelada']
CARRIER_OPTIONS = ['Estafeta', 'GOMSA', 'Rangel', 'Axionlog']

def generate_mock_data(num_orders, max_items, email):
    orders_ref = db.collection('orders')

    print("--- Starting Generation ---")
    print(f"Target Email: {email}")
    print(f"Count: {num_orders} orders | Max items per order: {max_items}")
    print("---------------------------\n")

    for i in range(num_orders):
        item_count = random.randint(1, max_items)
        order_status = random.choice(STATUS_OPTIONS)
        items = []
        total_amount = 0.0

        for _ in range(item_count):
            # JS: faker.commerce.price({ min: 5, max: 150 }) -> returns string, parsed to float
            price = round(random.uniform(5, 150), 2)
            qty = random.randint(1, 3)
            
            # Items usually share the order status or have their own
            item_status = random.choice(STATUS_OPTIONS)
            
            # Helper to determine if shipped/delivered for tracking info
            is_shipped = item_status in ['enviada', 'entregada']
            
            # JS used faker.string.alphanumeric(10)
            product_id = fake.bothify(text='?'*10, letters='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            # simplify alphanumeric generation
            product_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))

            items.append({
                'productId': product_id,
                # JS: faker.commerce.productName().toLowerCase()
                # Python Faker doesn't have commerce in core always behaving identical, checking... 
                # actually python faker has .bs() or similar, let's use a generic catch phrase or words if product_name not available
                # But widely it is available.
                'name': fake.bs().lower(), # placeholder if product_name fails, but let's try to match logic
                'quantity': str(qty),
                'priceAtPurchase': str(price),
                'image': f"https://picsum.photos/seed/{''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=8))}/200",
                'status': item_status,
                'carrier': random.choice(CARRIER_OPTIONS),
                'trackingNumber': ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=12)) if is_shipped else "",
                'shippedAt': datetime.datetime.now() if is_shipped else ""
            })
            
            # Try to get a better product name if possible
            # Standard Faker provider for products isn't always 'commerce.productName' in python.
            # Using 'catch_phrase' or 'bs' as fallback or just constructing one.
            # Actually, let's stick to what we have or improve.
            # 'name': fake.word() + " " + fake.word() is reasonable.
            items[-1]['name'] = f"{fake.word()} {fake.word()}".lower()

            total_amount += price * qty

        # Construct the order object
        order_data = {
            'userEmail': email,
            'userPhone': fake.phone_number(),
            'status': order_status,
            'totalAmount': round(total_amount, 2),
            'createdAt': datetime.datetime.now(),
            'shippingAddress': f"{fake.street_address()}, {fake.city()}",
            'items': items,
            'orderId': str(uuid.uuid4())[:8]
        }

        try:
            # Add to Firestore (letting Firestore generate the document ID)
            orders_ref.add(order_data)
            print(f"[{i + 1}/{num_orders}] ✅ Created order ({order_status}) with {item_count} items.")
        except Exception as e:
            print(f"❌ Error inserting order {i}: {e}")

    print("\n✨ All orders have been successfully inserted.")

if __name__ == "__main__":
    # Usage: python generate_orders.py <numOrders> <maxItems> <email>
    args = sys.argv[1:]
    
    # Defaults
    num_orders = 5
    max_items = 10
    target_email = "andresperezm@google.com"

    if len(args) >= 1:
        try:
            num_orders = int(args[0])
        except ValueError:
            pass
    
    if len(args) >= 2:
        try:
            max_items = int(args[1])
        except ValueError:
            pass

    if len(args) >= 3:
        target_email = args[2]

    generate_mock_data(num_orders, max_items, target_email)
