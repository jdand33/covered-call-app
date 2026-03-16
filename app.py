@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    expirations = []

    if request.method == "POST":
        ticker = request.form.get("ticker", "").upper().strip()
        risk_key = request.form.get("risk", "").strip()
        expiration = request.form.get("expiration", "").strip()

        # 1. Validate ticker first
        if not validate_ticker(ticker):
            return render_template("index.html", error=f"'{ticker}' is not a valid ticker with options.", expirations=[])

        # 2. Pull expiration list immediately
        expirations = get_expirations(ticker)

        if not expirations:
            return render_template("index.html", error="No expirations available.", expirations=[])

        # 3. If user hasn't selected an expiration yet, just show the list
        if expiration == "":
            return render_template("index.html", expirations=expirations)

        # 4. Validate expiration
        if expiration not in expirations:
            return render_template("index.html", error=f"{expiration} is not a valid expiration.", expirations=expirations)

        # 5. Validate risk
        if risk_key not in RISK_TO_DELTA:
            return render_template("index.html", error="Invalid risk level.", expirations=expirations)

        target_delta = RISK_TO_DELTA[risk_key]

        # 6. Pull closest delta strike
        result = get_closest_delta_strike(ticker, expiration, target_delta)
        if result is None:
            return render_template("index.html", error="Unable to pull option data.", expirations=expirations)

    return render_template("index.html", result=result, error=error, expirations=expirations)
