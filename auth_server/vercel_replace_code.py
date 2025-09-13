from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import json
import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'demo-secret-key-123')
CORS(app, supports_credentials=True)

# Simple user database (in production use real database)
users_db = {}

@app.route('/auth/google', methods=['POST'])
def google_auth():
    """Authenticate user with Google token (simplified for demo)"""
    try:
        data = request.get_json()
        email = data.get('email', 'demo@example.com')
        name = data.get('name', 'Demo User')
        
        # Create or get user
        if email not in users_db:
            # New user - create with trial
            trial_expiry = datetime.datetime.now() + datetime.timedelta(days=30)
            users_db[email] = {
                'email': email,
                'name': name,
                'subscription': {
                    'type': 'trial',
                    'expiry': trial_expiry,
                    'status': 'active'
                },
                'created_at': datetime.datetime.now()
            }
        
        user_data = users_db[email]
        subscription = user_data['subscription']
        
        # Check if subscription is still active
        if datetime.datetime.now() < subscription['expiry']:
            status = 'active'
            expires_at = subscription['expiry'].isoformat()
        else:
            status = 'expired'
            expires_at = None
        
        # Store session
        session['user'] = {
            'email': email,
            'name': name
        }
        
        return jsonify({
            'success': True,
            'user': {
                'email': email,
                'name': name
            },
            'subscription': {
                'status': status,
                'type': subscription['type'],
                'expires_at': expires_at
            }
        })
        
    except Exception as e:
        return jsonify({'error': 'Authentication failed'}), 500

@app.route('/auth/check', methods=['GET'])
def check_auth():
    """Check current authentication status"""
    try:
        user = session.get('user')
        if not user:
            return jsonify({'authenticated': False}), 401
            
        email = user['email']
        
        # Check user in simple database
        if email in users_db:
            user_data = users_db[email]
            subscription = user_data['subscription']
            
            # Check if subscription is still active
            if datetime.datetime.now() < subscription['expiry']:
                status = 'active'
                expires_at = subscription['expiry'].isoformat()
            else:
                status = 'expired'
                expires_at = None
                
            return jsonify({
                'authenticated': True,
                'user': user,
                'subscription': {
                    'status': status,
                    'type': subscription['type'],
                    'expires_at': expires_at
                }
            })
        else:
            return jsonify({'authenticated': False}), 401
        
    except Exception as e:
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
        if admin_key != os.environ.get('ADMIN_KEY', 'admin123'):
            return jsonify({'error': 'Unauthorized'}), 401
            
        users = []
        for email, user_data in users_db.items():
            users.append({
                'email': email,
                'name': user_data.get('name'),
                'subscription': user_data.get('subscription', {}),
                'created_at': user_data.get('created_at')
            })
            
        return jsonify({'users': users})
        
    except Exception as e:
        return jsonify({'error': 'Failed to list users'}), 500

@app.route('/admin/subscription', methods=['POST'])
def update_subscription():
    """Admin: Update user subscription"""
    try:
        admin_key = request.headers.get('X-Admin-Key')
        if admin_key != os.environ.get('ADMIN_KEY', 'admin123'):
            return jsonify({'error': 'Unauthorized'}), 401
            
        data = request.get_json()
        email = data.get('email')
        subscription_type = data.get('type', 'trial')
        days = data.get('days', 30)
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
            
        # Calculate expiry
        if subscription_type == 'lifetime':
            expiry = datetime.datetime(2099, 12, 31)
        else:
            expiry = datetime.datetime.now() + datetime.timedelta(days=days)
            
        # Update user subscription
        if email in users_db:
            users_db[email]['subscription'] = {
                'type': subscription_type,
                'expiry': expiry,
                'status': 'active'
            }
        else:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'subscription': {
                'type': subscription_type,
                'expiry': expiry.isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to update subscription'}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'users_count': len(users_db)
    })

@app.route('/', methods=['GET'])
def home():
    """Home page"""
    return jsonify({
        'message': 'AutoYoutube Authentication Server',
        'status': 'running',
        'endpoints': [
            '/auth/google (POST)',
            '/auth/check (GET)',
            '/auth/logout (POST)',
            '/admin/users (GET)',
            '/admin/subscription (POST)',
            '/health (GET)'
        ]
    })

if __name__ == '__main__':
    app.run(debug=True)
