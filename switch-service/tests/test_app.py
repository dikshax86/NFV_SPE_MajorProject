import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def _mock_firewall_response(status_code, json_data):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    return mock_resp


@patch('app.http_requests.post')
def test_route_allowed(mock_post, client):
    # First call = firewall (allowed), second call = monitor (logged)
    mock_post.side_effect = [
        _mock_firewall_response(200, {"status": "allowed", "message": "hello"}),
        _mock_firewall_response(200, {"status": "logged"})
    ]
    response = client.post('/route', json={"message": "hello"})
    assert response.status_code == 200
    assert response.json['status'] == 'allowed'


@patch('app.http_requests.post')
def test_route_blocked(mock_post, client):
    mock_post.side_effect = [
        _mock_firewall_response(403, {"status": "blocked", "reason": "IP blocked"}),
        _mock_firewall_response(200, {"status": "logged"})
    ]
    response = client.post('/route', json={"message": "hello"})
    assert response.status_code == 403
    assert response.json['status'] == 'blocked'


@patch('app.http_requests.post')
def test_route_firewall_down(mock_post, client):
    mock_post.side_effect = Exception("Connection refused")
    response = client.post('/route', json={"message": "hello"})
    assert response.status_code == 503


def test_route_invalid_json(client):
    response = client.post('/route',
        data="not json",
        content_type='application/json')
    assert response.status_code == 400


def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
