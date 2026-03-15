from flask import Flask, render_template, request
import yfinance as yf
from datetime import datetime

app = Flask(__name__)

# --- S&P 500 list for autocomplete (shortened for example) ---
SP500_TICKERS = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "MCD", "JPM", "XOM", "NVDA"
    # ... include your full list here ...
]

# --- Pretty labels for delta ranges ---
DELTA_LABELS = {
    "low": "Low (Δ ~0.10)",
    "low_moderate": "Low‑Moderate (Δ ~0.15)",
    "moderate": "Moderate (Δ ~0.20)",
    "moderate_high": "Moderate‑High (Δ ~0.25)",
    "high": "High (Δ ~0.30)"
}

# --- Numeric delta targets ---
DELTA_TARGETS = {
    "low": 0.10,
    "low_moderate": 0.15,
    "moderate": 0.20,
    "moderate_high": 0.25,
    "high": 0.30
}


# --- Validate ticker using fast_info ---
def is_valid_ticker(symbol: str) -> bool:
    try:
        t = yf.Ticker(symbol)
        info = t.fast_info
        return info is not None and "last_price" in info and info["last_price"] is not None
    except Exception:
        return False


# --- Pull expiration dates for ticker ---
def get_expiration_dates(ticker: str):
    try:
        t = yf.Ticker(ticker)
        return list(t.options or [])
    except Exception:
        return []


# --- Select call option closest to target delta ---
def select_call_for_delta(ticker: str, expiration: str, target_delta: float):
    t = yf.Ticker(ticker)
    info = t.fast_info
    spot = info["last_price"]

    chain = t.option_chain(expiration)
    calls = chain.calls.copy()

    # If delta exists, use it
    if "delta" in calls.columns:
        calls["delta_diff"] = (calls["delta"].abs() - target_delta).abs()
        best = calls.sort_values("delta_diff").iloc[0]
    else:
        # Fallback: closest strike above spot
        calls["strike_diff"] = (calls["strike"] - spot).abs()
        best = calls.sort_values("strike_diff").iloc[0]

    return {
        "ticker": ticker,
        "expiration": expiration,
        "spot": spot,
        "strike": float(best["strike"]),
        "bid": float(best.get("bid", 0.0)),
        "ask": float(best.get("ask", 0.0)),
        "last": float(best.get("lastPrice", best.get("last", 0.0))),
        "iv": float(best.get("impliedVolatility", 0.0)),
        "delta": float(best.get("delta", 0.0)),
    }


# --- Days to expiration ---
def compute_days_to_expiration(expiration: str) -> int:
    try:
        exp_date = datetime.strptime(expiration, "%Y-%m-%d").date()
        today = datetime.utcnow().date()
        return (exp_date - today).days
    except Exception:
        return 0


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    result = None

    ticker = "MCD"
    risk = "moderate"
    expiration = None

    if request.method == "POST":
        ticker = request.form.get("ticker", ticker).upper().strip()
        risk = request.form.get("risk", risk)
        expiration = request.form.get("expiration")

    # Validate ticker
    if not is_valid_ticker(ticker):
        error = f"'{ticker}' is not a valid ticker symbol."
        expirations = []
    else:
        expirations = get_expiration_dates(ticker)
        if not expiration and expirations:
            expiration = expirations[0]

    # Compute option selection
    if not error and expiration and risk in DELTA_TARGETS:
        target_delta = DELTA_TARGETS[risk]
        risk_label = DELTA_LABELS[risk]

        try:
            opt = select_call_for_delta(ticker, expiration, target_delta)
            days = compute_days_to_expiration(expiration)

            mid = (opt["bid"] + opt["ask"]) / 2 if (opt["bid"] and opt["ask"]) else opt["last"]
            premium = mid
            notional = opt["spot"] * 100
            raw_yield = premium * 100 / notional if notional else 0
            annualized_yield = raw_yield * (365 / days) if days > 0 else 0

            result = {
                "ticker": opt["ticker"],
                "expiration": opt["expiration"],
                "spot": round(opt["spot"], 2),
                "strike": round(opt["strike"], 2),
                "bid": round(opt["bid"], 2),
                "ask": round(opt["ask"], 2),
                "last": round(opt["last"], 2),
                "iv": round(opt["iv"] * 100, 2),
                "delta": round(opt["delta"], 3),
                "days": days,
                "premium": round(premium, 2),
                "raw_yield": round(raw_yield * 100, 2),
                "annualized_yield": round(annualized_yield * 100, 2),
                "risk_label": risk_label,
            }
        except Exception as e:
            error = f"Error pulling option data for {ticker}: {e}"

    last_inputs = {
        "ticker": ticker,
        "risk": risk,
        "expiration": expiration,
    }

    return render_template(
        "index.html",
        sp500=SP500_TICKERS,
        delta_labels=DELTA_LABELS,
        expirations=expirations,
        last_inputs=last_inputs,
        result=result,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True)
