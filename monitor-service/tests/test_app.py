import pytest
import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@patch('app.send_to_logstash')
def test_log_valid_request(mock_logstash, client):
    response = client.post('/log', json={
        "ip": "10.0.0.1",
        "message": "hello",
        "status": "allowed"
    })
    assert response.status_code == 200
    assert response.json['status'] == 'logged'
    mock_logstash.assert_called_once()


@patch('app.send_to_logstash')
def test_log_blocked_request(mock_logstash, client):
    response = client.post('/log', json={
        "ip": "192.168.1.10",
        "message": "hack attempt",
        "status": "blocked"
    })
    assert response.status_code == 200
    assert response.json['status'] == 'logged'


def test_log_invalid_json(client):
    response = client.post('/log',
        data="not json",
        content_type='application/json')
    assert response.status_code == 400


def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'
