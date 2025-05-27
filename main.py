from flask import Flask, request, jsonify
import requests
import os
import logging
import time
import hmac
import hashlib
import json

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
API_KEY = os.environ.get("BYBIT_API_KEY")
API_SECRET = os.environ.get("BYBIT_API_SECRET")
BASE_URL = "https://api-testnet.bybit.com"

# In-memory position state
position_state = "FLAT"  # can be "LONG" or "FLAT"

# === SIGNATURE GENERATOR ===
def generate_signature(secret, timestamp, recv_window, payload):
    param_str = f"{timestamp}{API_KEY}{recv_window}{payload}"
    return hmac.new(
        bytes(secret, "utf-8"),
        msg=bytes(param_str, "utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()

# === PLACE ORDER FUNCTION ===
def place_order(symbol, side, qty):
    logging.info(f"Placing {side} order: {qty} {symbol}")

    endpoint = f"{BASE_URL}/v5/order/create"
    url = endpoint

    recv_window = "5000"
    timestamp = str(int(time.time() * 1000))

    body = {
        "category": "linear",
        "symbol": symbol,
        "side": side.capitalize(),  # "Buy" or "Sell"
        "orderType": "Market",
        "qty": qty,
        "timeInForce": "GoodTillCancel"
    }

    payload_str = json.dumps(body, separators=(',', ':'))

    signature = generate_signature(API_SECRET, timestamp, recv_window, payload_str)

    headers = {
        "X-BYBIT-API-KEY": API_KEY,
        "X-BYBIT-SIGN": signature,
        "X-BYBIT-TIMESTAMP": timestamp,
        "X-BYBIT-RECV-WINDOW": recv_window,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, data=payload_str, headers=headers)
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

# === ROOT ENDPOINT ===
@app.route('/')
def index():
    return "Scalping Bot Webhook is Live"
