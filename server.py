from flask import Flask, jsonify
from main import run_daily_signal
import os
import threading

app = Flask(__name__)


def run_job():
    try:
        run_daily_signal()
    except Exception as e:
        print("Job failed:", e)


@app.route('/predict')
def index():
    thread = threading.Thread(target=run_job, daemon=True)
    thread.start()

    return jsonify({
        "status": "accepted",
        "message": "Signal job started"
    }), 202


@app.route('/')
def alive():
    return "✅ I am alive"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
