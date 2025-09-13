# AutoYoutube Authentication Server

Server-based authentication system using Google OAuth2 for AutoYoutube application.

## Features

- **Google OAuth2 Integration**: Secure authentication using Google accounts
- **Firebase Database**: User and subscription management
- **RESTful API**: Clean endpoints for authentication operations
- **Admin Panel**: User and subscription management
- **Session Management**: Secure session handling

## Setup

### 1. Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Google OAuth2 Configuration
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com

# Firebase Configuration (JSON string)
FIREBASE_CREDENTIALS={"type": "service_account", "project_id": "your-project", ...}

# Server Configuration
SECRET_KEY=your-secret-key-for-sessions
ADMIN_KEY=your-admin-key-for-management
```

### 2. Google OAuth2 Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Create OAuth2 credentials
5. Add authorized redirect URIs:
   - `http://localhost:8080/callback` (for development)
   - Your production callback URL

### 3. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project
3. Go to Project Settings > Service Accounts
4. Generate new private key
5. Copy the JSON content to `FIREBASE_CREDENTIALS` environment variable

### 4. Installation

```bash
pip install -r requirements.txt
```

### 5. Running the Server

#### Development
```bash
python app.py
```

#### Production (with Gunicorn)
```bash
gunicorn app:app
```

#### Deploy to Vercel
```bash
vercel --prod
```

## API Endpoints

### Authentication

#### `POST /auth/google`
Authenticate user with Google ID token.

**Request:**
```json
{
  "token": "google_id_token"
}
```

**Response:**
```json
{
  "success": true,
  "user": {
    "email": "user@example.com",
    "name": "User Name",
    "user_id": "123456789"
  },
  "subscription": {
    "status": "active",
    "type": "trial",
    "expires_at": "2024-01-01T00:00:00"
  }
}
```

#### `GET /auth/check`
Check current authentication status.

**Response:**
```json
{
  "authenticated": true,
  "user": {
    "email": "user@example.com",
    "name": "User Name",
    "user_id": "123456789"
  },
  "subscription": {
    "status": "active",
    "type": "trial",
    "expires_at": "2024-01-01T00:00:00"
  }
}
```

#### `POST /auth/logout`
Logout current user.

**Response:**
```json
{
  "success": true
}
```

### Admin Endpoints

#### `GET /admin/users`
List all users (requires admin key).

**Headers:**
```
X-Admin-Key: your-admin-key
```

**Response:**
```json
{
  "users": [
    {
      "email": "user@example.com",
      "name": "User Name",
      "subscription": {
        "type": "trial",
        "expiry": "2024-01-01T00:00:00"
      },
      "created_at": "2024-01-01T00:00:00"
    }
  ]
}
```

#### `POST /admin/subscription`
Update user subscription (requires admin key).

**Headers:**
```
X-Admin-Key: your-admin-key
```

**Request:**
```json
{
  "email": "user@example.com",
  "type": "lifetime",
  "days": 365
}
```

**Response:**
```json
{
  "success": true,
  "subscription": {
    "type": "lifetime",
    "expiry": "2099-12-31T00:00:00"
  }
}
```

### Health Check

#### `GET /health`
Server health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "firebase_connected": true
}
```

## Subscription Types

- **trial**: 1-day trial (automatically assigned to new users)
- **monthly**: 30-day subscription
- **yearly**: 365-day subscription  
- **lifetime**: Permanent access (expires 2099-12-31)

## Database Schema

### Users Collection

```json
{
  "email": "user@example.com",
  "name": "User Name",
  "user_id": "google_user_id",
  "subscription": {
    "type": "trial",
    "expiry": "2024-01-01T00:00:00",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  },
  "created_at": "2024-01-01T00:00:00"
}
```

## Security

- All endpoints use HTTPS in production
- Google ID tokens are verified server-side
- Session data is encrypted
- Admin endpoints require authentication key
- CORS is configured for client domains

## Error Handling

The server returns appropriate HTTP status codes:

- `200`: Success
- `400`: Bad Request (missing parameters)
- `401`: Unauthorized (invalid token/session)
- `500`: Internal Server Error

Error responses include descriptive messages:

```json
{
  "error": "Error description"
}
```
