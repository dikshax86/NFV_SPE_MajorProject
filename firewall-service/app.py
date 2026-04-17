from flask import Flask, request, jsonify

app = Flask(__name__)

# Blocked IPs - simulates a firewall rule table
BLOCKED_IPS = ["192.168.1.10"]

# Blocked keywords - simulates content filtering
BLOCKED_KEYWORDS = ["hack", "attack", "malware"]


@app.route('/check', methods=['POST'])
def check():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400

    ip = request.headers.get('X-Forwarded-For', 'unknown')
    message = data.get('message', '')

    # Check IP against blocklist
    if ip in BLOCKED_IPS:
        return jsonify({"status": "blocked", "reason": "IP blocked"}), 403

    # Check message content for malicious keywords
    for keyword in BLOCKED_KEYWORDS:
        if keyword in message.lower():
            return jsonify({"status": "blocked", "reason": f"Contains '{keyword}'"}), 403

    return jsonify({"status": "allowed", "message": message}), 200


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
