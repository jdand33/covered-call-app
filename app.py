import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TRADIER_TOKEN = os.getenv("TRADIER_TOKEN")
TRADIER_BASE = "https://api.tradier.com/v1"


def tradier_headers():
    return {
        "Authorization": f"Bearer {TRADIER_TOKEN}",
        "Accept": "application/json"
    }


# ============================
# GET EXPIRATIONS
# ============================
@app.route("/expirations", methods=["GET"])
def get_expirations():
    symbol = request.args.get("symbol", "").upper().strip()
    if not symbol:
        return jsonify({"error": "Missing symbol"}), 400

    url = f"{TRADIER_BASE}/markets/options/expirations"
    params = {"symbol": symbol, "includeAllRoots": "true", "strikes": "false"}

    r = requests.get(url, headers=tradier_headers(), params=params)
    if r.status_code != 200:
        return jsonify({"error": f"Tradier error {r.status_code}: {r.text}"}), 400

    data = r.json()
    expirations = data.get("expirations", {}).get("date", [])

    return jsonify({"symbol": symbol, "expirations": expirations})


# ============================
# GET OPTION CHAIN FOR ONE EXPIRATION
# ============================
@app.route("/chain", methods=["GET"])
def get_chain():
    symbol = request.args.get("symbol", "").upper().strip()
    expiration = request.args.get("expiration", "").strip()

    if not symbol:
        return jsonify({"error": "Missing symbol"}), 400
    if not expiration:
        return jsonify({"error": "Missing expiration"}), 400

    url = f"{TRADIER_BASE}/markets/options/chains"
    params = {"symbol": symbol, "expiration": expiration}

    r = requests.get(url, headers=tradier_headers(), params=params)
    if r.status_code != 200:
        return jsonify({"error": f"Tradier error {r.status_code}: {r.text}"}), 400

    data = r.json()
    options = data.get("options", {}).get("option", [])

    # Normalize output for your UI
    cleaned = []
    for opt in options:
        cleaned.append({
            "symbol": opt.get("symbol"),
            "type": opt.get("option_type"),
            "strike": opt.get("strike"),
            "expiration": opt.get("expiration_date"),
            "bid": opt.get("bid"),
            "ask": opt.get("ask"),
            "last": opt.get("last"),
            "delta": opt.get("greeks", {}).get("delta"),
            "gamma": opt.get("greeks", {}).get("gamma"),
            "theta": opt.get("greeks", {}).get("theta"),
            "vega": opt.get("greeks", {}).get("vega"),
            "rho": opt.get("greeks", {}).get("rho"),
            "iv": opt.get("greeks", {}).get("mid_iv"),
            "volume": opt.get("volume"),
            "open_interest": opt.get("open_interest"),
        })

    return jsonify({
        "symbol": symbol,
        "expiration": expiration,
        "count": len(cleaned),
        "options": cleaned
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok", "has_token": bool(TRADIER_TOKEN)})


if __name__ == "__main__":
    app.run(debug=True)
