from flask import Flask, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import os
import json
import datetime
from google.auth.transport import requests
from google.oauth2 import id_token
import firebase_admin
from firebase_admin import credentials, firestore
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')
CORS(app, supports_credentials=True)

# Google OAuth2 config
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')

# Firebase config
try:
    firebase_cred = json.loads(os.environ.get('FIREBASE_CREDENTIALS', '{}'))
    if firebase_cred:
        cred = credentials.Certificate(firebase_cred)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
    else:
        db = None
        print("Warning: Firebase not configured")
except Exception as e:
    print(f"Firebase initialization error: {e}")
    db = None

def verify_google_token(token):
    """Verify Google ID token"""
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
            
        return idinfo
    except ValueError as e:
        print(f"Token verification failed: {e}")
        return None

@app.route('/auth/google', methods=['POST'])
def google_auth():
    """Authenticate user with Google token"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Token required'}), 400
            
        # Verify Google token
        user_info = verify_google_token(token)
        if not user_info:
            return jsonify({'error': 'Invalid token'}), 401
            
        email = user_info['email']
        name = user_info['name']
        user_id = user_info['sub']
        
        # Check user subscription in database
        if db:
            user_doc = db.collection('users').document(email).get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                subscription = user_data.get('subscription', {})
                
                # Check if subscription is active
                expiry = subscription.get('expiry')
                if expiry and datetime.datetime.now() < expiry.replace(tzinfo=None):
                    status = 'active'
                    expires_at = expiry.isoformat()
                    subscription_type = subscription.get('type', 'unknown')
                else:
                    status = 'expired'
                    expires_at = None
                    subscription_type = 'none'
            else:
                # New user - create with trial
                trial_expiry = datetime.datetime.now() + datetime.timedelta(days=1)
                user_data = {
                    'email': email,
                    'name': name,
                    'user_id': user_id,
                    'subscription': {
                        'type': 'trial',
                        'expiry': trial_expiry,
                        'created_at': datetime.datetime.now()
                    },
                    'created_at': datetime.datetime.now()
                }
                
                db.collection('users').document(email).set(user_data)
                
                status = 'active'
                expires_at = trial_expiry.isoformat()
                subscription_type = 'trial'
        else:
            # No database - default to active for testing
            status = 'active'
            expires_at = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
            subscription_type = 'trial'
        
        # Store session
        session['user'] = {
            'email': email,
            'name': name,
            'user_id': user_id
        }
        
        return jsonify({
            'success': True,
            'user': {
                'email': email,
                'name': name,
                'user_id': user_id
            },
            'subscription': {
                'status': status,
                'type': subscription_type,
                'expires_at': expires_at
            }
        })
        
    except Exception as e:
        print(f"Auth error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

@app.route('/auth/check', methods=['GET'])
def check_auth():
    """Check current authentication status"""
    try:
        user = session.get('user')
        if not user:
            return jsonify({'authenticated': False}), 401
            
        email = user['email']
        
        # Check current subscription status
        if db:
            user_doc = db.collection('users').document(email).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                subscription = user_data.get('subscription', {})
                
                expiry = subscription.get('expiry')
                if expiry and datetime.datetime.now() < expiry.replace(tzinfo=None):
                    status = 'active'
                    expires_at = expiry.isoformat()
                    subscription_type = subscription.get('type', 'unknown')
                else:
                    status = 'expired'
                    expires_at = None
                    subscription_type = 'none'
            else:
                status = 'expired'
                expires_at = None
                subscription_type = 'none'
        else:
            # No database - default active
            status = 'active'
            expires_at = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
            subscription_type = 'trial'
        
        return jsonify({
            'authenticated': True,
            'user': user,
            'subscription': {
                'status': status,
                'type': subscription_type,
                'expires_at': expires_at
            }
        })
        
    except Exception as e:
        print(f"Check auth error: {e}")
        return jsonify({'error': 'Check failed'}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'success': True})

@app.route('/admin/users', methods=['GET'])
def list_users():
    """Admin: List all users"""
    try:
        admin_key = request.headers.get('X-Admin-Key')
        if admin_key != os.environ.get('ADMIN_KEY'):
            return jsonify({'error': 'Unauthorized'}), 401
            
        if not db:
            return jsonify({'error': 'Database not configured'}), 500
            
        users = []
        docs = db.collection('users').stream()
        
        for doc in docs:
            user_data = doc.to_dict()
            users.append({
                'email': doc.id,
                'name': user_data.get('name'),
                'subscription': user_data.get('subscription', {}),
                'created_at': user_data.get('created_at')
            })
            
        return jsonify({'users': users})
        
    except Exception as e:
        print(f"List users error: {e}")
        return jsonify({'error': 'Failed to list users'}), 500

@app.route('/admin/subscription', methods=['POST'])
def update_subscription():
    """Admin: Update user subscription"""
    try:
        admin_key = request.headers.get('X-Admin-Key')
        if admin_key != os.environ.get('ADMIN_KEY'):
            return jsonify({'error': 'Unauthorized'}), 401
            
        if not db:
            return jsonify({'error': 'Database not configured'}), 500
            
        data = request.get_json()
        email = data.get('email')
        subscription_type = data.get('type')  # 'trial', 'monthly', 'yearly', 'lifetime'
        days = data.get('days', 30)
        
        if not email or not subscription_type:
            return jsonify({'error': 'Email and type required'}), 400
            
        # Calculate expiry
        if subscription_type == 'lifetime':
            expiry = datetime.datetime(2099, 12, 31)
        else:
            expiry = datetime.datetime.now() + datetime.timedelta(days=days)
            
        # Update user subscription
        user_ref = db.collection('users').document(email)
        user_ref.update({
            'subscription': {
                'type': subscription_type,
                'expiry': expiry,
                'updated_at': datetime.datetime.now()
            }
        })
        
        return jsonify({
            'success': True,
            'subscription': {
                'type': subscription_type,
                'expiry': expiry.isoformat()
            }
        })
        
    except Exception as e:
        print(f"Update subscription error: {e}")
        return jsonify({'error': 'Failed to update subscription'}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'firebase_connected': db is not None
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
