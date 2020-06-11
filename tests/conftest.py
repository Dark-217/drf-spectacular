from importlib import import_module

import django
import pytest
from django.core import management


def pytest_configure(config):
    from django.conf import settings

    config.addinivalue_line(
        "markers", "contrib(name): mark required contrib package"
    )

    contrib_apps = [
        'rest_framework_jwt',
        'oauth2_provider',
    ]

    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:'
        }},
        SITE_ID=1,
        SECRET_KEY='not very secret in tests',
        USE_I18N=True,
        USE_L10N=True,
        STATIC_URL='/static/',
        ROOT_URLCONF='tests.urls',
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [],
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.debug',
                    ],
                },
            },
        ],
        MIDDLEWARE_CLASSES=(
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ),
        INSTALLED_APPS=(
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'rest_framework',
            'rest_framework.authtoken',
            *[app for app in contrib_apps if module_available(app)],
            'drf_spectacular',
            'tests',
        ),
        PASSWORD_HASHERS=(
            'django.contrib.auth.hashers.SHA1PasswordHasher',
            'django.contrib.auth.hashers.PBKDF2PasswordHasher',
            'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
            'django.contrib.auth.hashers.BCryptPasswordHasher',
            'django.contrib.auth.hashers.MD5PasswordHasher',
            'django.contrib.auth.hashers.CryptPasswordHasher',
        ),
        REST_FRAMEWORK={
            'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
        }
    )

    django.setup()
    # For whatever reason this works locally without an issue.
    # on TravisCI content_type table is missing in the sqlite db as
    # if no migration ran, but then why does it work locally?!
    management.call_command('migrate')


def pytest_addoption(parser):
    parser.addoption(
        "--skip-missing-contrib",
        action="store_true",
        default=False,
        help="skip tests depending on missing contrib packages"
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--skip-missing-contrib"):
        return
    skip_missing_contrib = pytest.mark.skip(reason="skip tests for missing contrib package")
    for item in items:
        for marker in item.own_markers:
            if marker.name == 'contrib':
                if not all([module_available(module_str) for module_str in marker.args]):
                    item.add_marker(skip_missing_contrib)


@pytest.fixture()
def no_warnings(capsys):
    """ make sure test emits no warnings """
    yield capsys
    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err


@pytest.fixture()
def warnings(capsys):
    """ make sure test emits no warnings """
    yield capsys
    captured = capsys.readouterr()
    assert captured.err


def module_available(module_str):
    try:
        import_module(module_str)
    except ImportError:
        return False
    else:
        return True
