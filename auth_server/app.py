from flask import Flask, request, jsonify, session
from flask_cors import CORS
import os
import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'demo-secret-key-123')
CORS(app, supports_credentials=True)

# Simple in-memory user database for demo
users_db = {}

@app.route('/auth/google', methods=['POST'])
def google_auth():
    """Authenticate user with Google token"""
    try:
        data = request.get_json()
        email = data.get('email', 'demo@example.com')
        name = data.get('name', 'Demo User')
        
        # Create or get user from in-memory database
        if email not in users_db:
            trial_expiry = datetime.datetime.now() + datetime.timedelta(days=30)
            users_db[email] = {
                'email': email,
                'name': name,
                'subscription': {
                    'type': 'trial',
                    'expiry': trial_expiry,
                    'status': 'active'
                }
            }
        
        user_data = users_db[email]
        subscription = user_data['subscription']
        
        # Check subscription status
        if datetime.datetime.now() < subscription['expiry']:
            status = 'active'
            expires_at = subscription['expiry'].isoformat()
        else:
            status = 'expired'
            expires_at = None
        
        # Store session
        session['user'] = {'email': email, 'name': name}
        
        return jsonify({
            'success': True,
            'user': {'email': email, 'name': name},
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
    user = session.get('user')
    if not user:
        return jsonify({'authenticated': False}), 401
    
    email = user['email']
    if email in users_db:
        user_data = users_db[email]
        subscription = user_data['subscription']
        
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
    return jsonify({'authenticated': False}), 401

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
    """Home endpoint"""
    return jsonify({
        'message': 'AutoYoutube Authentication Server',
        'status': 'running'
    })

if __name__ == '__main__':
    app.run(debug=True)
