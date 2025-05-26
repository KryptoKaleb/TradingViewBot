from flask import Flask, request, jsonify
import hmac
import hashlib
import requests
import time
import os

app = Flask(__name__)

API_KEY = os.getenv("BYBIT_API_KEY")
API_SECRET = os.getenv("BYBIT_API_SECRET")
BASE_URL = "https://api-testnet.bybit.com"

def place_order(symbol, side, qty):
    endpoint = "/v2/private/order/create"
    url = BASE_URL + endpoint
    timestamp = str(int(time.time() * 1000))
    params = f"api_key={API_KEY}&symbol={symbol}&side={side}&order_type=Market&qty={qty}&time_in_force=GoodTillCancel&timestamp={timestamp}"
    sign = hmac.new(bytes(API_SECRET, "utf-8"), params.encode("utf-8"), hashlib.sha256).hexdigest()
    final_params = params + f"&sign={sign}"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, data=final_params, headers=headers)
    return response.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if data is None:
        return jsonify({"error": "No data received"}), 400
    action = data.get("action")
    symbol = data.get("symbol", "SOLUSDT")
    qty = float(data.get("qty", 1))
    if action == "BUY":
        result = place_order(symbol, "Buy", qty)
    elif action == "SELL":
        result = place_order(symbol, "Sell", qty)
    else:
        return jsonify({"error": "Invalid action"}), 400
    return jsonify(result)
    if __name__ == "__main__":
        app.run(debug=True)
