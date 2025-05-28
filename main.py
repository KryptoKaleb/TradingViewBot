from flask import Flask, request, jsonify
import requests
import os
import logging
import time
import hmac
import hashlib
import base64
import urllib.parse

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Load Kraken API keys
API_KEY = os.environ.get("KRAKEN_API_KEY")
API_SECRET = os.environ.get("KRAKEN_API_SECRET")

# Position tracking (same logic you had before)
position_state = "FLAT"  # can be "LONG" or "FLAT"

# === KRAKEN ORDER FUNCTION ===
def place_order(symbol, side, qty):
    logging.info(f"Placing {side.upper()} order for {qty} {symbol}")

    url_path = "/0/private/AddOrder"
    api_url = "https://api.kraken.com" + url_path
    nonce = str(int(time.time() * 1000))

    # Kraken order payload
    data = {
        "nonce": nonce,
        "ordertype": "market",
        "type": side.lower(),  # 'buy' or 'sell'
        "volume": str(qty),
        "pair": symbol  # Kraken pair, e.g., 'SOLUSD'
    }

    post_data = urllib.parse.urlencode(data)
    message = (nonce + post_data).encode()
    sha256_hash = hashlib.sha256(message).digest()
    secret = base64.b64decode(API_SECRET)
    signature = hmac.new(secret, url_path.encode() + sha256_hash, hashlib.sha512)
    api_sign = base64.b64encode(signature.digest())

    headers = {
        "API-Key": API_KEY,
        "API-Sign": api_sign.decode()
    }

    try:
        response = requests.post(api_url, headers=headers, data=data)
        response.raise_for_status()
        logging.info("Kraken API response: %s", response.text)
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
    symbol = data.get("symbol")  # Must match Kraken pair format (e.g., 'SOLUSD')
    qty = data.get("qty")

    if not all([action, symbol, qty]):
        return jsonify({"error": "Missing required fields: action, symbol, qty"}), 400

    if action.upper() == "BUY":
        if position_state == "LONG":
            logging.info("Already in LONG position — skipping buy.")
            return jsonify({"message": "Already in position, no buy placed"}), 200

        place_order(symbol, "buy", qty)
        position_state = "LONG"
        return jsonify({"message": "Buy order placed"}), 200

    elif action.upper() == "SELL":
        if position_state == "FLAT":
            logging.info("Already in FLAT position — skipping sell.")
            return jsonify({"message": "No open position to sell"}), 200

        place_order(symbol, "sell", qty)
        position_state = "FLAT"
        return jsonify({"message": "Sell order placed"}), 200

    logging.warning("Unknown action received: %s", action)
    return jsonify({"error": "Unknown action"}), 400

# === ROOT ENDPOINT ===
@app.route('/')
def index():
    return "Kraken Scalping Bot Webhook is Live"
