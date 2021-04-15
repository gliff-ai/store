from .base import *

SECRET_KEY = get_env_value('SECRET_KEY')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': get_env_value('POSTGRES_DATABASE'),
        'HOST': get_env_value('POSTGRES_HOST'),
        'PASSWORD': get_env_value('POSTGRES_PASSWORD'),
        'USER': get_env_value('POSTGRES_USER'),
        'PORT': 5432,
    }
}