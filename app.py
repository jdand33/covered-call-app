from flask import Flask, render_template, request
import yfinance as yf
import numpy as np

app = Flask(__name__)

# -----------------------------
#  FULL S&P 500 TICKER LIST
# -----------------------------
SP500_TICKERS = [
    "AAPL","MSFT","AMZN","NVDA","GOOGL","GOOG","META","BRK.B","LLY","TSLA","UNH","JPM","V","XOM",
    "AVGO","PG","MA","HD","CVX","COST","ABBV","MRK","PEP","KO","WMT","BAC","ADBE","CRM","TMO",
    "CSCO","MCD","ACN","ABT","LIN","DHR","NFLX","WFC","INTC","TXN","NEE","PM","MS","HON","UNP",
    "AMGN","IBM","LOW","ORCL","SBUX","AMD","CAT","GS","GE","NOW","AMT","MDT","LMT","BLK","ISRG",
    "CVS","SYK","PLD","BKNG","GILD","MDLZ","ADI","CI","ZTS","ADP","DE","MMC","MO","REGN","SPGI",
    "ELV","TGT","BDX","SO","CB","CME","DUK","AON","PNC","ICE","NSC","CSX","EQIX","USB","SHW",
    "APD","FDX","ITW","EW","GM","ETN","AEP","PSA","HCA","MCO","ROP","AIG","COF","FIS","FISV",
    "MAR","KMB","D","ECL","EXC","AFL","ALL","A","MNST","LRCX","KLAC","NXPI","CDNS","SNPS","FTNT",
    "PAYX","ORLY","ROST","CTAS","AZO","PH","MSI","IDXX","WELL","HUM","TRV","PRU","MET","AEE",
    "ED","EIX","PEG","WEC","XEL"
]

# -----------------------------
#  VALIDATE TICKER
# -----------------------------
def validate_ticker(ticker: str) -> bool:
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info

        # Must have valid price
        if not info or info.last_price is None:
            return False

        # Must have option chain
        if not t.options:
            return False

        return True
    except Exception:
        return False

# -----------------------------
#  GET CLOSEST DELTA STRIKE
# -----------------------------
def get_closest_delta_strike(ticker: str, expiration: str, target_delta: float):
    try:
        t = yf.Ticker(ticker)
        chain = t.option_chain(expiration)
        calls = chain.calls

        # Remove rows without delta
        calls = calls.dropna(subset=["delta"])

        # Find strike with delta closest to target
        calls["abs_diff"] = (calls["delta"] - target_delta).abs()
        best = calls.loc[calls["abs_diff"].idxmin()]

        return {
            "strike": float(best["strike"]),
            "delta": float(best["delta"]),
            "bid": float(best["bid"]),
            "ask": float(best["ask"]),
            "last": float(best["lastPrice"]),
            "symbol": best["contractSymbol"]
        }

    except Exception as e:
        print("Error pulling delta:", e)
        return None

# -----------------------------
#  FLASK ROUTE
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None

    if request.method == "POST":
        ticker = request.form.get("ticker", "").upper().strip()
        expiration = request.form.get("expiration")
        target_delta = float(request.form.get("risk"))

        # Validate ticker
        if ticker not in SP500_TICKERS or not validate_ticker(ticker):
            return render_template(
                "index.html",
                error=f"'{ticker}' is not a valid S&P 500 ticker with options.",
                sp500=SP500_TICKERS
            )

        # Pull real delta + strike
        result = get_closest_delta_strike(ticker, expiration, target_delta)

        if result is None:
            return render_template(
                "index.html",
                error="Unable to pull real delta data.",
                sp500=SP500_TICKERS
            )

    return render_template(
        "index.html",
        result=result,
        sp500=SP500_TICKERS
    )

if __name__ == "__main__":
    app.run(debug=True)
