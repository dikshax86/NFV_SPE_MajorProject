from flask import Flask, request, jsonify
import requests as http_requests

app = Flask(__name__)

FIREWALL_URL = "http://firewall-service:5000/check"
MONITOR_URL = "http://monitor-service:5002/log"


@app.route('/route', methods=['POST'])
def route_request():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400

    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    message = data.get('message', '')

    # Step 1: Forward to Firewall for inspection
    try:
        fw_response = http_requests.post(
            FIREWALL_URL,
            json=data,
            headers={"X-Forwarded-For": client_ip}
        )
        fw_result = fw_response.json()
    except Exception as e:
        return jsonify({"error": "Firewall service unavailable", "details": str(e)}), 503

    # Step 2: Send log to Monitor (fire-and-forget)
    try:
        http_requests.post(MONITOR_URL, json={
            "ip": client_ip,
            "message": message,
            "status": fw_result.get('status', 'unknown')
        })
    except Exception:
        pass  # Don't fail if monitor is down

    # Step 3: Return firewall's response to client
    return jsonify(fw_result), fw_response.status_code


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
