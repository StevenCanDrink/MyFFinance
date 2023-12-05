import csv
import datetime
import pytz
import requests
import subprocess
import urllib
import uuid
import json
# from openai import OpenAI

# import asyncio
import os
from flask import redirect, render_template, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Prepare API request
    symbol = symbol.upper()
    end = datetime.datetime.now(pytz.timezone("US/Eastern"))
    start = end - datetime.timedelta(days=7)

    # Yahoo Finance API
    url = (
        f"https://query1.finance.yahoo.com/v7/finance/download/{urllib.parse.quote_plus(symbol)}"
        f"?period1={int(start.timestamp())}"
        f"&period2={int(end.timestamp())}"
        f"&interval=1d&events=history&includeAdjustedClose=true"
    )

    # Query API
    try:
        response = requests.get(
            url,
            cookies={"session": str(uuid.uuid4())},
            headers={"User-Agent": "python-requests", "Accept": "*/*"},
        )
        response.raise_for_status()

        # CSV header: Date,Open,High,Low,Close,Adj Close,Volume
        quotes = list(csv.DictReader(response.content.decode("utf-8").splitlines()))
        quotes.reverse()
        price = round(float(quotes[0]["Adj Close"]), 2)
        return {"name": symbol, "price": price, "symbol": symbol}
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


# async def askChatBot(content, dictionary):
#     api_key = "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"
#     client = OpenAI(api_key)
#     messages = [{"role": "user", "content": content}]

#     try:
#         context = " ".join(dictionary.values())
#     except AttributeError:
#         context = " "

#     conservation = [
#         {"role": "user", "content": content},
#         {"role": "bot", "content": context},
#     ]

#     response = client.chat.completions.create(
#         model="davinci-002",
#         messages=conservation,
#     )
#     # Add a new entry to the dictionary
#     dictionary.append(
#         {"role": "bot", "content": response.choices[0].message["content"]}
#     )
#     dictionary.append(messages)
#     return response
