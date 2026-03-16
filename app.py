from flask import Flask, render_template, request
import yfinance as yf
import requests
import os
from datetime import datetime

app = Flask(__name__)

# ---------------------------------------------------------
# TRADIER CONFIG
# ---------------------------------------------------------
TRADIER_KEY = os.getenv("TRADIER_KEY")

# Choose one:
TRADIER_URL = "https://sandbox.tradier.com/v1/markets/options/chains"
# For live data (real-time):
# TRADIER_URL = "https://api.tradier.com/v1/markets/options/chains"

HEADERS = {
    "Authorization": f"Bearer {TRADIER_KEY}",
    "Accept": "application/json"
}

# Risk tiers mapped to target deltas
RISK_TO_DELTA = {
    "very_safe": 0.10,
    "safe": 0.15,
    "moderate": 0.20,
    "aggressive": 0.25,
    "very_aggressive": 0.30
}

# ---------------------------------------------------------
# VALIDATE TICKER
# ---------------------------------------------------------
def validate_ticker(ticker: str) -> bool:
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info

        if not info:
            print("DEBUG: fast_info empty")
            return False

        if not getattr(info, "last_price", None):
            print("DEBUG: last_price missing")
            return False

        return True

    except Exception as e:
        print("VALIDATE_TICKER EXCEPTION:", e)
        return False


# ---------------------------------------------------------
# GET EXPIRATIONS (YFINANCE)
# ---------------------------------------------------------
def get_expirations(ticker: str):
    try:
        t = yf.Ticker(ticker)
        expirations = t.options
        print("DEBUG: Expirations:", expirations)
        return expirations
    except Exception as e:
        print("GET_EXPIRATIONS EXCEPTION:", e)
        return []


# ---------------------------------------------------------
# GET OPTION CHAIN FROM TRADIER
# ---------------------------------------------------------
def get_tradier_chain(ticker: str, expiration: str):
    params = {
        "symbol": ticker,
        "expiration": expiration,
        "greeks": "true"
    }

    print("DEBUG: Tradier request:", params)

    try:
        r = requests.get(TRADIER_URL, headers=HEADERS, params=params)

        if r.status_code != 200:
            print("TRADIER ERROR:", r.text)
            return None

        data = r.json()

        if "options" not in data or data["options"] is None:
            print("TRADIER: No options returned")
            return None

        return data["options"]["option"]

    except Exception as e:
        print("TRADIER REQUEST EXCEPTION:", e)
        return None


# ---------------------------------------------------------
# SELECT STRIKE BY DELTA
# ---------------------------------------------------------
def select_by_delta(options, target_delta):
    best = None
    best_diff = 999

    for opt in options:
        if opt["option_type"] != "call":
            continue

        delta = opt.get("greeks", {}).get("delta")
        if delta is None:
            continue

        diff = abs(delta - target_delta)
        if diff < best_diff:
            best_diff = diff
            best = opt

    return best


# ---------------------------------------------------------
# MAIN ROUTE
# ---------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    expirations = []

    if request.method == "POST":
        action = request.form.get("action")
        ticker = request.form.get("ticker", "").upper().strip()
        expiration = request.form.get("expiration", "").strip()
        risk_key = request.form.get("risk", "").strip()

        print("\n=== FORM DEBUG ===")
        print("Action:", action)
        print("Ticker:", ticker)
        print("Expiration:", expiration)
        print("Risk:", risk_key)
        print("===================\n")

        # Validate ticker
        if not ticker:
            return render_template("index.html",
                                   error="Please enter a ticker.",
                                   expirations=[])

        if not validate_ticker(ticker):
            return render_template("index.html",
                                   error=f"'{ticker}' is not a valid ticker.",
                                   expirations=[])

        # Load expirations
        expirations = get_expirations(ticker)
        if not expirations:
            return render_template("index.html",
                                   error="No expirations available.",
                                   expirations=[])

        # If user clicked "Get Expirations"
        if action == "load":
            return render_template("index.html",
                                   expirations=expirations)

        # User clicked "Calculate"
        if expiration not in expirations:
            return render_template("index.html",
                                   error="Invalid expiration.",
                                   expirations=expirations)

        target_delta = RISK_TO_DELTA[risk_key]

        # Get Tradier chain
        chain = get_tradier_chain(ticker, expiration)
        if chain is None:
            return render_template("index.html",
                                   error="Unable to pull option data.",
                                   expirations=expirations)

        # Select strike by delta
        best = select_by_delta(chain, target_delta)
        if best is None:
            return render_template("index.html",
                                   error="No valid delta data.",
                                   expirations=expirations)

        # ---------------------------------------------------------
        # BUILD RESULT OBJECT
        # ---------------------------------------------------------
        t = yf.Ticker(ticker)
        fi = t.fast_info
        stock_price = getattr(fi, "last_price", None)

        exp_date = datetime.strptime(expiration, "%Y-%m-%d")
        today = datetime.utcnow()
        days_out = (exp_date - today).days

        bid = best.get("bid", 0)
        ask = best.get("ask", 0)
        mid = round((bid + ask) / 2, 2)
        premium = round(mid * 100, 2)

        delta = best.get("greeks", {}).get("delta")
        assign_prob = round(abs(delta) * 100, 1) if delta else None

        result = {
            "ticker": ticker,
            "stock_price": stock_price,
            "expiration": expiration,
            "days_out": days_out,
            "risk_label": risk_key.replace("_", " ").title(),
            "strike": best["strike"],
            "iv": best.get("greeks", {}).get("iv"),
            "assign_prob": assign_prob,
            "mid": mid,
            "premium": premium
        }

    return render_template("index.html",
                           result=result,
                           error=error,
                           expirations=expirations)


# ---------------------------------------------------------
# RUN APP
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
