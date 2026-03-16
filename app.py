from flask import Flask, render_template, request
import yfinance as yf

app = Flask(__name__)

def validate_ticker(ticker: str) -> bool:
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        if not info or info.last_price is None:
            return False
        if not t.options:
            return False
        return True
    except:
        return False

def get_closest_delta_strike(ticker: str, expiration: str, target_delta: float):
    try:
        t = yf.Ticker(ticker)
        chain = t.option_chain(expiration)
        calls = chain.calls.dropna(subset=["delta"])
        calls["abs_diff"] = (calls["delta"] - target_delta).abs()
        best = calls.loc[calls["abs_diff"].idxmin()]
        return {
            "symbol": best["contractSymbol"],
            "strike": float(best["strike"]),
            "delta": float(best["delta"]),
            "bid": float(best["bid"]),
            "ask": float(best["ask"]),
            "last": float(best["lastPrice"])
        }
    except:
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None

    if request.method == "POST":
        ticker = request.form.get("ticker", "").upper().strip()
        expiration = request.form.get("expiration", "").strip()
        risk_raw = request.form.get("risk", "").strip()

        if not ticker or not expiration or not risk_raw:
            error = "All fields are required."
            return render_template("index.html", error=error)

        try:
            target_delta = float(risk_raw)
        except:
            return render_template("index.html", error="Invalid delta value.")

        if not validate_ticker(ticker):
            return render_template("index.html", error=f"'{ticker}' is not a valid ticker with options.")

        result = get_closest_delta_strike(ticker, expiration, target_delta)
        if result is None:
            return render_template("index.html", error="Unable to pull option data for that expiration.")

    return render_template("index.html", result=result, error=error)

if __name__ == "__main__":
    app.run(debug=True)
