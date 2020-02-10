"""
Django settings for YtManager project.

Generated by 'django-admin startproject' using Django 1.11.11.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os
import sys
import logging
from os.path import dirname as up

URL_BASE = get_global_opt('UrlBase', cfg, env_variable='YTSM_URL_BASE', fallback="")

#
# Basic Django stuff
#
ALLOWED_HOSTS = ['*']
SESSION_COOKIE_AGE = 3600 * 30      # one month

# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'dynamic_preferences',
    'dynamic_preferences.users.apps.UserPreferencesConfig',
    'YtManagerApp.apps.YtManagerAppConfig',
    'crispy_forms',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'channels',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'YtManager.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.media',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'dynamic_preferences.processors.global_preferences',
            ],
        },
    },
]

WSGI_APPLICATION = 'YtManager.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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

LOGIN_REDIRECT_URL = URL_BASE+'/'
LOGIN_URL = URL_BASE+'/login'


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Thumbnails
THUMBNAIL_SIZE_VIDEO = (410, 230)
THUMBNAIL_SIZE_SUBSCRIPTION = (250, 250)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = URL_BASE+'/static/'
MEDIA_URL = URL_BASE+'/media/'


# Misc Django stuff

CRISPY_TEMPLATE_PACK = 'bootstrap4'

LOG_FORMAT = '%(asctime)s|%(process)d|%(thread)d|%(name)s|%(filename)s|%(lineno)d|%(levelname)s|%(message)s'
CONSOLE_LOG_FORMAT = '%(asctime)s | %(name)s | %(filename)s:%(lineno)d | %(levelname)s | %(message)s'

#
# Directories
#

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
PROJECT_ROOT = up(up(os.path.dirname(__file__)))            # Project root
BASE_DIR = up(os.path.dirname(__file__))                    # Base dir of the application

CONFIG_DIR = os.getenv("YTSM_CONFIG_DIR", os.path.join(PROJECT_ROOT, "config"))
DATA_DIR = os.getenv("YTSM_DATA_DIR", os.path.join(PROJECT_ROOT, "data"))

STATIC_ROOT = os.path.join(PROJECT_ROOT, "static")
MEDIA_ROOT = os.path.join(DATA_DIR, 'media')


#
# Defaults
#
_DEFAULT_DEBUG = False

_DEFAULT_SECRET_KEY = '^zv8@i2h!ko2lo=%ivq(9e#x=%q*i^^)6#4@(juzdx%&0c+9a0'

_DEFAULT_DATABASE = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DATA_DIR, 'ytmanager.db'),
        'HOST': None,
        'USER': None,
        'PASSWORD': None,
        'PORT': None,
    }

CONFIG_ERRORS = []
CONFIG_WARNINGS = []

# These are just to make inspector happy, they will be set in the load_config_ini() method
DEBUG = None
SECRET_KEY = None
DATABASES = None
LOG_LEVEL = None

#
# Config parser options
#
CFG_PARSER_OPTS = {
    'PROJECT_ROOT': PROJECT_ROOT,
    'BASE_DIR': BASE_DIR,
    'CONFIG_DIR': CONFIG_DIR,
    'DATA_DIR': DATA_DIR,
}

ASGI_APPLICATION = 'YtManager.routing.application'


#
# Load globals from config.ini
#
def get_global_opt(name, cfgparser, env_variable=None, fallback=None, boolean=False, integer=False):
    """
    Reads a configuration option, in the following order:
    1. environment variable
    2. config parser
    3. fallback

    :param integer:
    :param cfgparser:
    :param name:
    :param env_variable:
    :param fallback:
    :param boolean:
    :return:
    """
    # Get from environment variable
    if env_variable is not None:
        value = os.getenv(env_variable)

        if value is not None and boolean:
            return value.lower() in ['true', 't', 'on', 'yes', 'y', '1']
        elif value is not None and integer:
            try:
                return int(value)
            except ValueError:
                CONFIG_WARNINGS.append(f'Environment variable {env_variable}: value must be an integer value!')
        elif value is not None:
            return value

    # Get from config parser
    if boolean:
        try:
            return cfgparser.getboolean('global', name, fallback=fallback, vars=CFG_PARSER_OPTS)
        except ValueError:
            CONFIG_WARNINGS.append(f'config.ini file: Value set for option global.{name} is not valid! '
                                   f'Valid options: true, false, on, off.')
            return fallback

    if integer:
        try:
            return cfgparser.getint('global', name, fallback=fallback, vars=CFG_PARSER_OPTS)
        except ValueError:
            CONFIG_WARNINGS.append(f'config.ini file: Value set for option global.{name} must be an integer number! ')
            return fallback

    return cfgparser.get('global', name, fallback=fallback, vars=CFG_PARSER_OPTS)


def load_config_ini():
    from configparser import ConfigParser
    from YtManagerApp.utils.extended_interpolation_with_env import ExtendedInterpolatorWithEnv
    import dj_database_url

    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        logging.info(f"Using data directory {DATA_DIR}")
    except OSError as e:
        print(f'CRITICAL ERROR! Cannot create data directory {DATA_DIR}! {e}', file=sys.stderr)
        return

    cfg = ConfigParser(allow_no_value=True, interpolation=ExtendedInterpolatorWithEnv())

    cfg_file = os.path.join(CONFIG_DIR, "config.ini")
    read_ok = cfg.read([cfg_file])

    if cfg_file not in read_ok:
        CONFIG_ERRORS.append(f'Configuration file {cfg_file} could not be read! Please make sure the file is in the '
                             'right place, and it has read permissions.')

    # Debug
    global DEBUG
    DEBUG = get_global_opt('Debug', cfg, env_variable='YTSM_DEBUG', fallback=_DEFAULT_DEBUG, boolean=True)

    # Secret key
    # SECURITY WARNING: keep the secret key used in production secret!
    global SECRET_KEY
    SECRET_KEY = get_global_opt('SecretKey', cfg, env_variable='YTSM_SECRET_KEY', fallback=_DEFAULT_SECRET_KEY)

    # Database
    global DATABASES
    DATABASES = {
        'default': _DEFAULT_DATABASE
    }

    if cfg.has_option('global', 'DatabaseURL'):
        DATABASES['default'] = dj_database_url.parse(cfg.get('global', 'DatabaseURL', vars=CFG_PARSER_OPTS),
                                                     conn_max_age=600)

    else:
        DATABASES['default'] = {
            'ENGINE': get_global_opt('DatabaseEngine', cfg,
                                     env_variable='YTSM_DB_ENGINE', fallback=_DEFAULT_DATABASE['ENGINE']),
            'NAME': get_global_opt('DatabaseName', cfg,
                                   env_variable='YTSM_DB_NAME', fallback=_DEFAULT_DATABASE['NAME']),
            'HOST': get_global_opt('DatabaseHost', cfg,
                                   env_variable='YTSM_DB_HOST', fallback=_DEFAULT_DATABASE['HOST']),
            'USER': get_global_opt('DatabaseUser', cfg,
                                   env_variable='YTSM_DB_USER', fallback=_DEFAULT_DATABASE['USER']),
            'PASSWORD': get_global_opt('DatabasePassword', cfg,
                                       env_variable='YTSM_DB_PASSWORD', fallback=_DEFAULT_DATABASE['PASSWORD']),
            'PORT': get_global_opt('DatabasePort', cfg,
                                   env_variable='YTSM_DB_PORT', fallback=_DEFAULT_DATABASE['PORT']),
        }

    # Log settings
    global LOG_LEVEL
    log_level_str = get_global_opt('LogLevel', cfg, env_variable='YTSM_LOG_LEVEL', fallback='INFO')

    try:
        LOG_LEVEL = getattr(logging, log_level_str)
    except AttributeError:
        CONFIG_WARNINGS.append(f'Invalid log level {log_level_str}. '
                               f'Valid options are: DEBUG, INFO, WARN, ERROR, CRITICAL.')
        print("Invalid log level " + LOG_LEVEL)
        LOG_LEVEL = logging.INFO


load_config_ini()
