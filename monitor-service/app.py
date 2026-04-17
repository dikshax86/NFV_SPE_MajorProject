from flask import Flask, request, jsonify
import logging
import json
import socket
from datetime import datetime

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('monitor-service')

# Logstash configuration
LOGSTASH_HOST = 'logstash'
LOGSTASH_PORT = 5000


def send_to_logstash(log_data):
    """Send log entry to Logstash via TCP."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect((LOGSTASH_HOST, LOGSTASH_PORT))
        log_data['timestamp'] = datetime.utcnow().isoformat()
        log_data['service'] = 'nfv-monitor'
        sock.send((json.dumps(log_data) + '\n').encode())
        sock.close()
    except Exception as e:
        logger.warning(f"Could not send to Logstash: {e}")


@app.route('/log', methods=['POST'])
def log():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400

    ip = data.get('ip', 'unknown')
    message = data.get('message', '')
    status = data.get('status', 'unknown')

    # Log to console
    logger.info(f"[LOG] IP: {ip} | Message: {message} | Status: {status}")

    # Send to Logstash (ELK integration)
    send_to_logstash({
        "ip": ip,
        "message": message,
        "status": status
    })

    return jsonify({"status": "logged"}), 200


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
