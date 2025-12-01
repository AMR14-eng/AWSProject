import pytest
from app import app

@pytest.fixture
def test_app():
    """Fixture para crear la app de testing"""
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(test_app):
    """Fixture para el cliente de testing"""
    return test_app.test_client()