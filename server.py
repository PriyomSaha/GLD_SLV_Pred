from flask import Flask
from main import run_daily_signal
import os

app = Flask(__name__)


@app.route('/predict')
def index():
    run_daily_signal()
    return "✅ Signal sent to Telegram."


@app.route('/')
def alive():
    return "✅ I am alive"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
