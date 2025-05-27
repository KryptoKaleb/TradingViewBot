from flask import Flask, request, jsonify
import requests
import os
import logging

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)

# Environment variables (already loaded in Render)
API_KEY = os.environ.get("BYBIT_API_KEY")
API_SECRET = os.environ.get("BYBIT_API_SECRET")
BASE_URL = "https://api-testnet.bybit.com"

# Simple in-memory position tracker
position_state = "FLAT"  # can be "LONG" or "FLAT"

# === PLACE ORDER FUNCTION ===
def place_order(symbol, side, qty):
    logging.info(f"Placing {side} order: {qty} {symbol}")

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

    try:
        response = requests.post(endpoint, json=data, headers=headers)
        response.raise_for_status()
        logging.info("Bybit API response: %s", response.text)
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Order failed: {e}")
        return {"error": str(e)}

# === WEBHOOK HANDLER ===
@app.route('/webhook', methods=['POST'])
def webhook():
    global position_state

    try:
        data = request.get_json(force=True)
        logging.info("Webhook received: %s", data)
    except Exception as e:
        logging.error("Error parsing webhook JSON: %s", e)
        return jsonify({"error": "Invalid JSON"}), 400

    action = data.get("action")
    symbol = data.get("symbol")
    qty = data.get("qty")

    if not all([action, symbol, qty]):
        return jsonify({"error": "Missing required fields: action, symbol, qty"}), 400

    if action.upper() == "BUY":
        if position_state == "LONG":
            logging.info("Already in LONG position — skipping buy.")
            return jsonify({"message": "Already in position, no buy placed"}), 200

        place_order(symbol, "Buy", qty)
        position_state = "LONG"
        return jsonify({"message": "Buy order placed"}), 200

    elif action.upper() == "SELL":
        if position_state == "FLAT":
            logging.info("Already in FLAT position — skipping sell.")
            return jsonify({"message": "No open position to sell"}), 200

        place_order(symbol, "Sell", qty)
        position_state = "FLAT"
        return jsonify({"message": "Sell order placed"}), 200

    logging.warning("Unknown action received: %s", action)
    return jsonify({"error": "Unknown action"}), 400

# === OPTIONAL: Basic root endpoint ===
@app.route('/')
def index():
    return "Scalping Bot Webhook is Live"
