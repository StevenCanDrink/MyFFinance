import os

from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
import asyncio
from helpers import apology, login_required, lookup, usd, askChatBot

# Configure application
app = Flask(__name__)


if __name__ == "__main__":
    app.run(debug=True, port=os.getenv("PORT", default=5000))

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    messages = [
        {"role": "system", "content": "You are a helpful and kind AI Assistant."},
    ]
    """Show portfolio of stocks"""
    if session["user_id"] == "":
        return redirect("/login")
    users = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
    purchased = db.execute(
        "SELECT userid,SUM(quantity) AS quantity,symbol FROM Purchased GROUP BY userid,symbol HAVING userid = ?",
        users[0]["id"],
    )
    prices = [lookup(item["symbol"])["price"] for item in purchased]
    quantity = [purchase["quantity"] for purchase in purchased]
    combined_list = [(x, y) for x, y in zip(purchased, prices)]
    sum = 0
    for price, quantity in zip(prices, quantity):
        sum += price * quantity

    return render_template(
        "index.html",
        users=users,
        purchased=purchased,
        combined=combined_list,
        price=prices,
        sum=sum,
    )


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        foo = request.form.get("symbol")
        try:
            shares = eval(request.form.get("shares"))
            flash(shares)
            symbol = lookup(foo)
            conditions = [
                not shares,
                not foo,
                not symbol,
                type(shares) != int,
                shares < 0,
            ]
            if any(conditions):
                return apology("INVALID 400")
            cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
            sumPrice = shares * symbol["price"]
            if cash[0]["cash"] < sumPrice:
                return apology("NOT ENOUGHT CASH")
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.execute(
                "UPDATE users SET cash = ? WHERE id = ?",
                cash[0]["cash"] - sumPrice,
                session["user_id"],
            )
            db.execute(
                "INSERT INTO Purchased(userid,totalprice,quantity,time,symbol) VALUES(?,?,?,?,?)",
                session["user_id"],
                sumPrice,
                shares,
                current_date,
                symbol["symbol"],
            )

            flash("BUY SUCCESS")
            return redirect("/")
        except (ValueError, TypeError):
            return apology("INVALID 400")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    histories = db.execute("SELECT * FROM Purchased")
    historiesWithIndex = list(enumerate(histories))
    return render_template("history.html", histories=historiesWithIndex)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        username = request.form.get("username")
        password = request.form.get("password")
        if not username:
            return apology("must provide username", 403)

        # Ensure password was submitted

        elif not password:
            return apology("must provide password", 403)
        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        # Ensure username exists and password is correct
        isValidPassword = False
        for row in rows:
            isValidPassword = check_password_hash(row["hash"], password)
        if len(rows) != 1 or not isValidPassword:
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        conditions = [not symbol, not lookup(symbol)]
        if any(conditions):
            return apology("INVALID 400")
        respFromAPI = lookup(symbol)
        respFromAPI["price"] = usd(respFromAPI["price"])
        return jsonify(respFromAPI)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        name = request.form.get("username")
        password = request.form.get("password")
        retype = request.form.get("confirmation")
        queryName = db.execute("SELECT * FROM users WHERE username = ?", name)
        conditions = [
            not name,
            not password,
            not retype,
            password != retype,
            len(queryName) != 0,
        ]
        if any(conditions):
            return apology("INVALID 400")
        hashedPassword = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (username,hash) VALUES(?,?)", name, hashedPassword
        )
        flash("Registered")
        session["user_id"] = db.execute("SELECT * FROM users WHERE username = ?", name)[
            0
        ]["id"]
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    purchased = db.execute(
        "SELECT userid,symbol,SUM(quantity) FROM Purchased GROUP BY userid,symbol HAVING userid = ?",
        session["user_id"],
    )

    if request.method == "POST":
        cash = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        if not shares:
            return apology("FILL SHARES YOU WANT TO SELL")
        shares = int(request.form.get("shares"))
        symbolOfPerson = db.execute(
            "SELECT userid,symbol,SUM(quantity) AS quantity FROM Purchased GROUP BY userid,symbol HAVING userid = ? AND symbol = ?",
            session["user_id"],
            symbol,
        )
        if symbolOfPerson[0]["quantity"] < shares or shares < 0:
            return apology("SHARES IS OVERFLOW")
        sumPrice = lookup(symbol)["price"] * shares
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "UPDATE users SET cash = ? WHERE id = ?",
            cash[0]["cash"] + sumPrice,
            session["user_id"],
        )
        db.execute(
            "INSERT INTO Purchased(userid,totalprice,quantity,time,symbol) VALUES(?,?,?,?,?)",
            session["user_id"],
            sumPrice,
            -shares,
            current_time,
            symbol,
        )
        return redirect("/")
    else:
        return render_template("sell.html", purchased=purchased)


@app.route("/changepwd", methods=["GET", "POST"])
@login_required
def changepassword():
    if request.method == "POST":
        old = request.form.get("old")
        new = request.form.get("new")
        retype = request.form.get("retype")
        row = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])
        isValidPwd = check_password_hash(row[0]["hash"], old)
        if not isValidPwd or new != retype:
            return apology("WRONG PASSWORD")
        hashPwd = generate_password_hash(new)
        db.execute(
            "UPDATE users SET hash = ? WHERE id = ?", hashPwd, session["user_id"]
        )
        flash("CHANGE PASSWORD SUCCEED")
        return redirect("/")
    else:
        return render_template("changepwd.html")
