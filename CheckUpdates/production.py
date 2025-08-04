import os

from .settings import *

# Cloudinary storage settings
os.getenv = os.getenv
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv(
        "CLOUDINARY_CLOUD_NAME"
    ),  # Cloudinary cloud name from environment variables
    "API_KEY": os.getenv("CLOUDINARY_API_KEY"),  # Cloudinary API key
    "API_SECRET": os.getenv("CLOUDINARY_API_SECRET"),  # Cloudinary API secret
}

# General settings for production
DEBUG = False  # Turn off debug mode for production
DEBUG_PROPAGATE_EXCEPTIONS = (
    False  # Prevent debug information from propagating in production
)

# Allowed hosts for the application
ALLOWED_HOSTS = []  # Set this to your allowed production hosts

# Trusted origins for CSRF protection, dynamically generated from allowed hosts
CSRF_TRUSTED_ORIGINS = ["https://" + host for host in ALLOWED_HOSTS]

# Redis URL configuration for caching, fetched from environment
REDISCLOUD_URL = os.getenv("REDISCLOUD_URL")

# Database configuration (PostgreSQL) for production
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",  # Use PostgreSQL as the database engine
        "NAME": os.getenv("DB_NAME"),  # Database name from environment
        "USER": os.getenv("DB_USER"),  # Database user
        "PASSWORD": os.getenv("DB_PASS"),  # Database password
        "HOST": os.getenv("DB_HOST"),  # Database host
        "PORT": os.getenv("DB_PORT"),  # Database port
    }
}

# Remove debug toolbar in production for performance and security
INSTALLED_APPS.remove("debug_toolbar")
MIDDLEWARE.remove("debug_toolbar.middleware.DebugToolbarMiddleware")

# Email backend settings for SMTP
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"  # Use SMTP for sending emails
)
EMAIL_USE_TLS = True  # Enable TLS for email security
EMAIL_USE_SSL = False  # Disable SSL (only TLS is enabled)
EMAIL_HOST = "smtp.gmail.com"  # Email host (Gmail)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")  # Email user
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")  # Email password
EMAIL_PORT = 587  # SMTP port for TLS
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER  # Default email sender address

# Storage configuration
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",  # Media files on Cloudinary
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        # Static files with WhiteNoise for compressed storage
    },
}

# Content Security Policy (CSP) - Strictly Enforced
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],  # Only allow loading from same origin
        "img-src": [
            "'self'",
            "https://res.cloudinary.com",
        ],  # Allow images from Cloudinary
        "media-src": [
            "'self'",
            "https://res.cloudinary.com",
        ],  # Allow media files from Cloudinary
        "script-src": ["'self'"],  # Restrict JavaScript to same-origin
        "style-src": ["'self'"],  # Restrict CSS to same-origin
        "font-src": ["'self'"],  # Restrict font files to same-origin
        "connect-src": ["'self'"],  # Allow connections only to same-origin
        "frame-ancestors": ["'self'"],  # Only allow embedding from the same origin
        "form-action": ["'self'"],  # Allow form submissions only to the same origin
        "report-uri": "/csp-report/",  # Report violations to this endpoint
    }
}

# Cookie and session security settings
CSRF_COOKIE_SECURE = True  # Secure CSRF cookie, only sent over HTTPS
SECURE_HSTS_SECONDS = 31536000  # Enable HTTP Strict Transport Security for 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True  # Apply HSTS to all subdomains
SECURE_HSTS_PRELOAD = True  # Allow HSTS preloading in browsers
SECURE_BROWSER_XSS_FILTER = True  # Enable XSS filtering
SECURE_CONTENT_TYPE_NOSNIFF = (
    True  # Prevent the browser from MIME-type sniffing  # noqa
)
SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)  # Header for identifying secure requests
SECURE_SSL_REDIRECT = True  # Redirect all HTTP requests to HTTPS
SESSION_COOKIE_SECURE = True  # Ensure session cookie is only sent over HTTPS
X_FRAME_OPTIONS = "DENY"  # Prevent the site from being embedded in iframes

# Additional cookie settings
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript from accessing session cookies
CSRF_COOKIE_HTTPONLY = (
    False  # Allow CSRF cookie to be accessible to JavaScript (if required)
)
CSRF_COOKIE_SAMESITE = "Lax"  # CSRF cookie is only sent on same-site requests  # noqa
