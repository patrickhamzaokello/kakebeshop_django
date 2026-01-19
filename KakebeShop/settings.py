
import datetime
import os
from pathlib import Path
import environ
import os
from decouple import config, Csv

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('DJANGO_SECRET_KEY')
SOCIAL_SECRET= config('SOCIAL_SECRET')

WEB_GOOGLE_CLIENT_ID = config('WEB_GOOGLE_CLIENT_ID')
IOS_GOOGLE_CLIENT_ID = config('IOS_GOOGLE_CLIENT_ID')
ANDROID_GOOGLE_CLIENT_ID = config('ANDROID_GOOGLE_CLIENT_ID')

TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN')
TWILIO_VERIFY_SERVICE_SID = config('TWILIO_VERIFY_SERVICE_SID')

AWS_REGION = config('AWS_REGION')
AWS_S3_BUCKET_NAME = config('AWS_S3_BUCKET_NAME')
AWS_S3_UPLOAD_EXPIRE_SECONDS = 300

AWS_CLOUDFRONT_DOMAIN = config('AWS_CLOUDFRONT_DOMAIN')


ALLOWED_HOSTS = [
    'backend.kakebeshop.com',
    'localhost',
    '127.0.0.1',
    '192.168.1.3'
]

GOOGLE_CLIENT_IDS = [
    WEB_GOOGLE_CLIENT_ID,  # Web client
    IOS_GOOGLE_CLIENT_ID,     # iOS client
    ANDROID_GOOGLE_CLIENT_ID, # Android client
]

APPLE_CLIENT_ID = "com.kakebe.shop.dev"
APPLE_CLIENT_IDS = ["com.kakebe.shop.dev", "com.kakebe.shop"]  # List of valid client IDs

CSRF_TRUSTED_ORIGINS = ["https://backend.kakebeshop.com"]

AUTH_USER_MODEL = 'authentication.User'
# Application definition

# Listing limits per merchant
LISTINGS_PER_MERCHANT_LIMIT = 100
LISTINGS_FEATURED_LIMIT = 50

# View/Contact increment rate limits (in seconds)
LISTING_VIEW_INCREMENT_COOLDOWN = 300  # 5 minutes
LISTING_CONTACT_INCREMENT_COOLDOWN = 3600  # 1 hour

# Image settings
LISTING_MAX_IMAGES = 10
LISTING_IMAGE_VARIANTS = ['thumb', 'medium', 'large', 'original']

# Listing expiry (optional)
LISTING_DEFAULT_EXPIRY_DAYS = 30

# Featured listing duration (optional)
FEATURED_LISTING_DEFAULT_DAYS = 7

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Marketplace Listings API',
    'DESCRIPTION': 'API for managing marketplace listings',
    'VERSION': '1.0.0',
}

DJANGO_APPS  = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'drf_spectacular'
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_yasg',
    'django_celery_results',
    'django_celery_beat'
]

LOCAL_APPS = [
    'kakebe_apps.authentication',
    'kakebe_apps.social_auth',
    'kakebe_apps.cart',
    'kakebe_apps.orders',
    'kakebe_apps.categories',
    'kakebe_apps.engagement',
    'kakebe_apps.listings',
    'kakebe_apps.location',
    'kakebe_apps.merchants',
    'kakebe_apps.promotions',
    'kakebe_apps.transactions',
    'kakebe_apps.notifications',
    'kakebe_apps.imagehandler'
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

SWAGGER_SETTINGS = {
    'USE_SESSION_AUTH': False,
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    }
}


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'KakebeShop.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'KakebeShop.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': config('DB_DRIVER', default='django.db.backends.postgresql'),
        'NAME': config('KAKEBE_DB_NAME'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('PG_HOST'),
        'PORT': config('PG_PORT', default='5432'),
    }
}
CELERY_BROKER_URL = config('REDIS_DATABASE_SERVER_HOST')
CELERY_RESULT_BACKEND = config('REDIS_DATABASE_SERVER_HOST')
# Celery task settings
CELERY_TASK_DEFAULT_QUEUE = 'kakebeshop_tasks'
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
    'result_chord_prefix': 'kakebeshop-chord-',
}

# Celery Configuration
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Celery Beat (Scheduler)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Task time limits
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes

# Worker configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000


# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE


CORS_ORIGIN_WHITELIST = [
    "http://localhost:8000",
    "https://newsapi.mwonya.com",
    "http://127.0.0.1:8080"
]

CORS_ORIGIN_REGEX_WHITELIST = [
    r"^https://\w+\.mwonya\.com",
]

SITE_ID = 1

REST_USE_JWT = True
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS =  ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'NON_FIELD_ERRORS_KEY': 'error',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': datetime.timedelta(minutes=10),
    'REFRESH_TOKEN_LIFETIME': datetime.timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,  # Use this for rolling tokens
    'BLACKLIST_AFTER_ROTATION': True,
}

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS =  [BASE_DIR / 'kakebe_static']
STATIC_ROOT =  BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}



EMAIL_USE_TLS = True
EMAIL_HOST = config('EMAIL_SERVER_HOST')
EMAIL_PORT = config('EMAIL_PORT')  #465 (or 587 for TLS)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
EMAIL_PLUNK_API_KEY = config('EMAIL_PLUNK_API_KEY')

EMAIL_SENDER_NAME = 'Kakebeshop'
EMAIL_REPLY_TO = 'support@kakebeshop.com'

# Company Information (used in email templates)
COMPANY_NAME = 'KAKEBE SHOP'
COMPANY_WEBSITE = 'https://kakebeshop.com'
SUPPORT_EMAIL = 'support@kakebeshop.com'

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@kakebeshop.com')




# ============================================================================
# PUSH NOTIFICATION CONFIGURATION
# ============================================================================

# External Push Notification Service
PUSH_NOTIFICATION_API_URL = config('PUSH_NOTIFICATION_API_URL', default='')
PUSH_NOTIFICATION_API_KEY = config('PUSH_NOTIFICATION_API_KEY', default='')


# ============================================================================
# FRONTEND URL
# ============================================================================

FRONTEND_URL = config('FRONTEND_URL', default='https://kakebeshop.com')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_DATABASE_SERVER_HOST'),
        'KEY_PREFIX': 'kakebeshop',
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/kakebe_shop_logs.log',
            'formatter': 'verbose',
        },
        'notification_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/notifications.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'kakebe_shop_logs': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.core.mail': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'kakebe_apps.notifications': {
            'handlers': ['notification_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['notification_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
