"""
Pytest configuration and fixtures.
"""
import pytest
from django.conf import settings


@pytest.fixture(scope='session')
def django_db_setup():
    """Configure Django test database."""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }


@pytest.fixture
def api_client():
    """Create an API client for testing."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, django_user_model):
    """Create an authenticated API client."""
    user = django_user_model.objects.create_user(
        email='test@example.com',
        username='testuser',
        password='testpass123',
    )
    api_client.force_authenticate(user=user)
    return api_client
