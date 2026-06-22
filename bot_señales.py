from flask import Flask, request
import requests

app = Flask(__name__)

TELEGRAM_TOKEN = "TU_TOKEN"
CHAT_ID = "TU_CHAT_ID"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    signal = data.get("signal")
    symbol = data.get("symbol")
    price  = data.get("price")

    if signal == "BUY":
        msg = f"📊 SMC BOT\n📈 BUY {symbol}\n💰 Price: {price}"
        send_telegram(msg)

    if signal == "SELL":
        msg = f"📊 SMC BOT\n📉 SELL {symbol}\n💰 Price: {price}"
        send_telegram(msg)

    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
