import os
import datetime
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin SDK
# Inherits credentials from the environment (Cloud Run)
firebase_admin.initialize_app()
db = firestore.client()

app = Flask(__name__)

@app.route('/orders', methods=['GET'])
def get_orders():
    try:
        email = request.args.get('email')
        status = request.args.get('status')
        print(f"Email: {email}, Status: {status}")

        if not email:
            return jsonify({'error': 'User email is required.'}), 400

        orders_ref = db.collection('orders')
        query = orders_ref.where(filter=firestore.FieldFilter('userEmail', '==', email))

        if status:
            query = query.where(filter=firestore.FieldFilter('status', '==', status))

        docs = query.stream()
        orders = []
        
        # Check if empty - stream() doesn't have an empty property easily checkable without consuming
        # So we just consume it.
        found_docs = list(docs)
        
        if not found_docs:
             return jsonify([]), 200

        for doc in found_docs:
            data = doc.to_dict()
            # Handle createdAt - assuming it's a Firestore Timestamp
            created_at = data.get('createdAt')
            if created_at:
                # Firestore timestamp to datetime
                dt = created_at
                if hasattr(created_at, 'date'): # Logic if it's already a datetime or Timestamp
                     pass # it is datetime-like
                else:
                     # Fallback if it's not a datetime object (unlikely with firestore client)
                     pass
                
                # Format: YYYY-MM-DD HH:MM
                formatted_created_at = created_at.strftime('%Y-%m-%d %H:%M')
            else:
                formatted_created_at = None

            orders.append({
                'orderId': data.get('orderId'),
                'status': data.get('status'),
                'createdAt': formatted_created_at,
                'itemCount': len(data.get('items', [])),
                'totalAmount': data.get('totalAmount'),
            })

        return jsonify(orders), 200

    except Exception as e:
        print(f"Error fetching orders: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/orders/<order_id>', methods=['GET'])
def get_order_by_id(order_id):
    try:
        email = request.args.get('email')
        
        if not email:
            return jsonify({'error': 'User email is required.'}), 400

        print(f"Fetching order {order_id} for email {email}")

        orders_ref = db.collection('orders')
        query = orders_ref.where(filter=firestore.FieldFilter('userEmail', '==', email))\
                          .where(filter=firestore.FieldFilter('orderId', '==', order_id))\
                          .limit(1)
        
        docs = list(query.stream())

        if not docs:
            return jsonify({'error': 'Order not found.'}), 404

        order_data = docs[0].to_dict()
        
        # Handle createdAt serialization
        created_at = order_data.get('createdAt')
        if created_at:
             # Assuming it's a datetime/Timestamp object
             if hasattr(created_at, 'strftime'):
                order_data['createdAt'] = created_at.strftime('%Y-%m-%d %H:%M')
             else:
                order_data['createdAt'] = str(created_at)

        return jsonify(order_data), 200

    except Exception as e:
        print(f"Error fetching order: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/items', methods=['GET'])
def get_items():
    try:
        email = request.args.get('email')
        order_id = request.args.get('orderId')
        print(f"Email: {email}, Order ID: {order_id}")

        if not email:
            return jsonify({'error': 'User email is required.'}), 400

        orders_ref = db.collection('orders')
        query = orders_ref.where(filter=firestore.FieldFilter('userEmail', '==', email))

        if order_id:
            query = query.where(filter=firestore.FieldFilter('orderId', '==', order_id))

        docs = list(query.stream())
        if not docs:
            return jsonify([]), 200

        purchased_items = []
        for doc in docs:
            order_data = doc.to_dict()
            items = order_data.get('items')
            if items and isinstance(items, list):
                for item in items:
                    item_copy = item.copy()
                    item_copy['orderId'] = order_data.get('orderId')
                    purchased_items.append(item_copy)

        return jsonify(purchased_items), 200

    except Exception as e:
        print(f"Error fetching purchased items: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/items/<product_id>', methods=['GET'])
def get_item(product_id):
    try:
        email = request.args.get('email')
        order_id = request.args.get('orderId')

        if not email:
            return jsonify({'error': 'User email is required.'}), 400

        orders_ref = db.collection('orders')
        query = orders_ref.where(filter=firestore.FieldFilter('userEmail', '==', email))

        if order_id:
            query = query.where(filter=firestore.FieldFilter('orderId', '==', order_id))

        docs = query.stream()

        for doc in docs:
            order_data = doc.to_dict()
            items = order_data.get('items', [])
            for item in items:
                if item.get('productId') == product_id:
                    item_copy = item.copy()
                    item_copy['orderId'] = order_data.get('orderId')
                    return jsonify(item_copy), 200

        return jsonify({'error': 'Item not found.'}), 404

    except Exception as e:
        print(f"Error fetching item: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/orders/remove-item', methods=['POST'])
def remove_item():
    try:
        data = request.get_json()
        email = data.get('email')
        order_id = data.get('orderId')
        product_id = data.get('productId')

        if not email or not order_id or not product_id:
            return jsonify({'error': 'Email, orderId, and productId are required.'}), 400

        orders_ref = db.collection('orders')
        query = orders_ref.where(filter=firestore.FieldFilter('userEmail', '==', email))\
                          .where(filter=firestore.FieldFilter('orderId', '==', order_id))\
                          .limit(1)
        
        docs = list(query.stream())

        if not docs:
            return jsonify({'error': 'Order not found.'}), 404

        order_doc = docs[0]
        order_data = order_doc.to_dict()
        items = order_data.get('items', [])

        item_to_remove = next((item for item in items if item.get('productId') == product_id), None)

        if not item_to_remove:
            return jsonify({'error': 'Item not found in order.'}), 404

        new_items = [item for item in items if item.get('productId') != product_id]
        
        # Recalculate total amount
        new_total_amount = sum(
            float(item.get('priceAtPurchase', 0)) * int(item.get('quantity', 0))
            for item in new_items
        )

        order_doc.reference.update({
            'items': new_items,
            'totalAmount': round(new_total_amount, 2)
        })

        return jsonify({'message': 'Item removed successfully.'}), 200

    except Exception as e:
        print(f"Error removing item from order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/orders/cancel', methods=['POST'])
def cancel_order():
    try:
        data = request.get_json()
        email = data.get('email')
        order_id = data.get('orderId')

        if not email or not order_id:
             return jsonify({'error': 'Email and orderId are required.'}), 400

        orders_ref = db.collection('orders')
        query = orders_ref.where(filter=firestore.FieldFilter('userEmail', '==', email))\
                          .where(filter=firestore.FieldFilter('orderId', '==', order_id))\
                          .limit(1)
        
        docs = list(query.stream())

        if not docs:
            return jsonify({'error': 'Order not found.'}), 404

        order_doc = docs[0]
        order_data = order_doc.to_dict()

        if order_data.get('status') == 'cancelada':
             return jsonify({'message': 'Order is already cancelled.'}), 200

        order_doc.reference.update({'status': 'cancelada'})

        return jsonify({'message': f'Order {order_id} cancelled successfully.'}), 200

    except Exception as e:
        print(f"Error cancelling order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/orders/feedback', methods=['POST'])
def add_feedback():
    try:
        data = request.get_json()
        email = data.get('email')
        order_id = data.get('orderId')
        feedback = data.get('feedback')

        if not email or not order_id or not feedback:
            return jsonify({'error': 'Email, orderId, and feedback are required.'}), 400

        print(f"Feedback for order {order_id} by {email}: {feedback}")

        return jsonify({'message': 'Feedback added successfully.'}), 200

    except Exception as e:
        print(f"Error adding feedback to order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/date', methods=['GET'])
def get_date():
    try:
        now = datetime.datetime.now()
        return jsonify({
            'iso': now.isoformat(),
            'date': now.strftime('%d/%m/%Y'),
            'time': now.strftime('%X'),
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to retrieve date.'}), 500

@app.route('/users', methods=['POST'])
def create_user():
    try:
        data = request.get_json()
        phone_number = data.get('phoneNumber')
        user_email = data.get('userEmail')
        user_name = data.get('userName')

        if not phone_number or not user_email or not user_name:
            return jsonify({'error': 'phoneNumber, userEmail, and userName are required.'}), 400

        # Check if user already exists
        users_ref = db.collection('users')
        query = users_ref.where(filter=firestore.FieldFilter('phoneNumber', '==', phone_number)).limit(1)
        docs = list(query.stream())

        if docs:
            # Update existing user
            user_doc = docs[0]
            user_doc.reference.update({
                'userEmail': user_email,
                'userName': user_name
            })
            return jsonify({'message': f'User {phone_number} updated successfully.'}), 200
        else:
            # Create new user
            users_ref.add({
                'phoneNumber': phone_number,
                'userEmail': user_email,
                'userName': user_name,
                'createdAt': firestore.SERVER_TIMESTAMP
            })
            return jsonify({'message': f'User {phone_number} created successfully.'}), 201

    except Exception as e:
        print(f"Error creating/updating user: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/users', methods=['GET'])
def get_user():
    try:
        phone_number = request.args.get('phoneNumber')
        
        if not phone_number:
            return jsonify({'error': 'phoneNumber is required.'}), 400
            
        print(f"Querying for user with phoneNumber: '{phone_number}'")

        users_ref = db.collection('users')
        query = users_ref.where(filter=firestore.FieldFilter('phoneNumber', '==', phone_number)).limit(1)
        docs = list(query.stream())

        if not docs:
             return jsonify({'error': 'User not found.'}), 404

        user_data = docs[0].to_dict()
        # Convert timestamp to string if present
        if 'createdAt' in user_data:
             user_data['createdAt'] = str(user_data['createdAt'])

        return jsonify(user_data), 200

    except Exception as e:
        print(f"Error fetching user: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
