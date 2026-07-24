"""
Local server that:
1. Receives readings from your hardware (POST /api/data)
2. Stores the latest + recent history in memory
3. Serves a live web dashboard (GET /)

Run it, then expose it to the internet with a tunnel (see SETUP.md).
"""

from flask import Flask, request, jsonify, render_template
from datetime import datetime
from collections import deque
import threading

app = Flask(__name__)

# Keep the last 200 readings in memory. Swap for SQLite/Postgres if you need
# real persistence across restarts.
HISTORY_LIMIT = 200
history = deque(maxlen=HISTORY_LIMIT)
lock = threading.Lock()

# Optional: simple shared-secret check so random people on the internet
# can't post fake data to your dashboard. Set this to something private,
# and send the same value as a header from your hardware.
DEVICE_TOKEN = "change-me-to-a-secret-string"


@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/api/data", methods=["POST"])
def receive_data():
    """Hardware devices POST JSON readings here, e.g.:
    {"temperature": 24.5, "humidity": 61.2}
    You can add any fields you want -- the dashboard will just show
    whatever keys are present in the latest reading.
    """
    token = request.headers.get("X-Device-Token")
    if token != DEVICE_TOKEN:
        return jsonify({"error": "unauthorized"}), 401

    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "expected JSON body"}), 400

    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **payload,
    }

    with lock:
        history.append(entry)

    return jsonify({"status": "ok", "stored": entry}), 201


@app.route("/api/data", methods=["GET"])
def get_data():
    """Dashboard polls this to get the latest readings."""
    with lock:
        data = list(history)
    return jsonify(data)


@app.route("/api/health")
def health():
    return jsonify({"status": "running"})


if __name__ == "__main__":
    # host="0.0.0.0" is important: it makes the server reachable from
    # other devices on your network (and from a tunnel), not just localhost.
    app.run(host="0.0.0.0", port=8000, debug=True)