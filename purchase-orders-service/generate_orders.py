
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

REALISTIC_PRODUCTS = [
    # Electronics
    {"name": "Laptop Pro 15", "image": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=200"},
    {"name": "Smartphone X", "image": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=200"},
    {"name": "Auriculares Bluetooth", "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=200"},
    {"name": "Reloj Inteligente", "image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=200"},
    {"name": "Cámara Mirrorless", "image": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=200"},
    {"name": "Tablet Air", "image": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=200"},
    {"name": "Consola de Videojuegos", "image": "https://images.unsplash.com/photo-1486401899868-0e435ed85128?w=200"},
    {"name": "Altavoz Inteligente", "image": "https://images.unsplash.com/photo-1589492477829-5e65395b66cc?w=200"},
    {"name": "Drone 4K", "image": "https://images.unsplash.com/photo-1507582020474-9a35b7d455d9?w=200"},
    {"name": "Teclado Mecánico", "image": "https://images.unsplash.com/photo-1511467687858-23d96c32e4ae?w=200"},

    # Clothing
    {"name": "Camiseta Algodón", "image": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=200"},
    {"name": "Jeans Clásicos", "image": "https://images.unsplash.com/photo-1542272454315-4c01d7abdf4a?w=200"},
    {"name": "Zapatillas Running", "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=200"},
    {"name": "Chaqueta de Cuero", "image": "https://images.unsplash.com/photo-1551028919-ac66e613ec65?w=200"},
    {"name": "Vestido de Verano", "image": "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=200"},
    {"name": "Gorra Deportiva", "image": "https://images.unsplash.com/photo-1588850561407-ed78c282e89b?w=200"},
    {"name": "Bufanda de Lana", "image": "https://images.unsplash.com/photo-1520903920248-269e3a628172?w=200"},
    {"name": "Guantes de Invierno", "image": "https://images.unsplash.com/photo-1517260739837-13359146141b?w=200"},
    {"name": "Mochila Urbana", "image": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=200"},
    {"name": "Gafas de Sol", "image": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=200"},

    # Home
    {"name": "Cafetera Express", "image": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=200"},
    {"name": "Lámpara de Mesa", "image": "https://images.unsplash.com/photo-1507473888900-52e1adad5468?w=200"},
    {"name": "Planta Decorativa", "image": "https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=200"},
    {"name": "Cojín Suave", "image": "https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?w=200"},
    {"name": "Juego de Sábanas", "image": "https://images.unsplash.com/photo-1522771753035-0a15395376b5?w=200"},
    {"name": "Espejo Redondo", "image": "https://images.unsplash.com/photo-1618220179428-22790b461013?w=200"},
    {"name": "Reloj de Pared", "image": "https://images.unsplash.com/photo-1563861826100-9cb868fdbe1c?w=200"},
    {"name": "Alfombra Moderna", "image": "https://images.unsplash.com/photo-1575412629239-2a0753f7f093?w=200"},
    {"name": "Veladora Aromática", "image": "https://images.unsplash.com/photo-1602037299865-4dd136ac5ae4?w=200"},
    {"name": "Mesa Auxiliar", "image": "https://images.unsplash.com/photo-1532372320572-cda25653a26d?w=200"},
    
    # Sports
    {"name": "Balón de Fútbol", "image": "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=200"},
    {"name": "Raqueta de Tenis", "image": "https://images.unsplash.com/photo-1622279457486-62dcc4a431d6?w=200"},
    {"name": "Pesas de Gimnasio", "image": "https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?w=200"},
    {"name": "Esterilla de Yoga", "image": "https://images.unsplash.com/photo-1592432678016-e910b452f9a2?w=200"},
    {"name": "Botella Deportiva", "image": "https://images.unsplash.com/photo-1602143407151-ca11143ea27d?w=200"}
]

TARGET_EMAILS = [
    "dmartinezg@google.com",
    "karentorres@google.com",
    "maumelendez@google.com",
    "pablopv@google.com",
    "andresperezm@google.com",
    "philiped@google.com"
]

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
            
            # Randomly select a product
            product_data = random.choice(REALISTIC_PRODUCTS)

            # JS used faker.string.alphanumeric(10)
            # simplify alphanumeric generation
            product_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))

            items.append({
                'productId': product_id,
                'name': product_data['name'],
                'quantity': str(qty),
                'priceAtPurchase': str(price),
                'image': product_data['image'],
                'status': item_status,
                'carrier': random.choice(CARRIER_OPTIONS),
                'trackingNumber': ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=12)) if is_shipped else "",
                'shippedAt': datetime.datetime.now() if is_shipped else ""
            })
            

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
    target_email = None

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

    if target_email:
        generate_mock_data(num_orders, max_items, target_email)
    else:
        print(f"Generating orders for {len(TARGET_EMAILS)} target emails...")
        for email in TARGET_EMAILS:
            generate_mock_data(num_orders, max_items, email)

    generate_mock_data(num_orders, max_items, target_email) if target_email and False else None # prevent double run if logic above changes
