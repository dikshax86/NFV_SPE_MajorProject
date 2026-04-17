import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_allowed_request(client):
    response = client.post('/check',
        json={"message": "hello world"},
        headers={"X-Forwarded-For": "10.0.0.1"})
    assert response.status_code == 200
    assert response.json['status'] == 'allowed'
    assert response.json['message'] == 'hello world'


def test_blocked_ip(client):
    response = client.post('/check',
        json={"message": "hello"},
        headers={"X-Forwarded-For": "192.168.1.10"})
    assert response.status_code == 403
    assert response.json['status'] == 'blocked'
    assert response.json['reason'] == 'IP blocked'


def test_blocked_keyword_hack(client):
    response = client.post('/check',
        json={"message": "hack the system"},
        headers={"X-Forwarded-For": "10.0.0.1"})
    assert response.status_code == 403
    assert response.json['status'] == 'blocked'


def test_blocked_keyword_attack(client):
    response = client.post('/check',
        json={"message": "launch an attack"},
        headers={"X-Forwarded-For": "10.0.0.1"})
    assert response.status_code == 403


def test_blocked_keyword_malware(client):
    response = client.post('/check',
        json={"message": "contains malware inside"},
        headers={"X-Forwarded-For": "10.0.0.1"})
    assert response.status_code == 403


def test_invalid_json(client):
    response = client.post('/check',
        data="not json",
        content_type='application/json')
    assert response.status_code == 400
    assert response.json['error'] == 'Invalid JSON'


def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'
