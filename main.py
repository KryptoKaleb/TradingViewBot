from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Environment variables (already loaded in Render)
API_KEY = os.environ.get("BYBIT_API_KEY")
API_SECRET = os.environ.get("BYBIT_API_SECRET")
BASE_URL = "https://api-testnet.bybit.com"

# Simple in-memory position tracker
position_state = "FLAT"  # could be "LONG" or "FLAT"

# === PLACE ORDER FUNCTION ===
def place_order(symbol, side, qty):
    print(f"Placing {side} order: {qty} {symbol}")

    endpoint = f"{BASE_URL}/v5/order/create"
    headers = {
        "X-BYBIT-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "category": "linear",
        "symbol": symbol,
        "side": side.capitalize(),  # "Buy" or "Sell"
        "orderType": "Market",
        "qty": qty,
        "timeInForce": "GoodTillCancel"
    }

    response = requests.post(endpoint, json=data, headers=headers)
    print("Bybit Response:", response.text)
    return response.json()


# === WEBHOOK HANDLER ===
@app.route('/webhook', methods=['POST'])
def webhook():
    global position_state
    data = request.get_json()

    print("Webhook received:", data)

    action = data.get("action")
    symbol = data.get("symbol")
    qty = data.get("qty")

    if not action or not symbol or not qty:
        return jsonify({"error": "Invalid webhook data"}), 400

    if action.upper() == "BUY":
        if position_state == "LONG":
            print("Already in LONG, skipping buy")
            return jsonify({"message": "Already in position, no buy placed"}), 200

        place_order(symbol, "Buy", qty)
        position_state = "LONG"
        return jsonify({"message": "Buy order placed"}), 200

    elif action.upper() == "SELL":
        if position_state == "FLAT":
            print("Already flat, skipping sell")
            return jsonify({"message": "No open position to sell"}), 200

        place_order(symbol, "Sell", qty)
        position_state = "FLAT"
        return jsonify({"message": "Sell order placed"}), 200

    return jsonify({"error": "Unknown action"}), 400


# Optional: Basic root endpoint
@app.route('/')
def index():
    return "Scalping Bot Webhook Live"
