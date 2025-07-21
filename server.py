from flask import Flask
from main import run_daily_signal

app = Flask(__name__)


@app.route('/')
def index():
    run_daily_signal()
    return "✅ Signal sent to Telegram."


@app.route('/alive')
def alive():
    return "✅ I am alive"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
