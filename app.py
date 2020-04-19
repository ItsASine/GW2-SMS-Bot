import json
import math
import os
from functools import wraps

import requests
from flask import abort
from flask import Flask
from flask import jsonify
from flask import request
from flask import send_file
from twilio.request_validator import RequestValidator

app = Flask(__name__)


# Blatantly using the awesome Twilio tutorial code
# https://www.twilio.com/docs/usage/tutorials/how-to-secure-your-flask-app-by-validating-incoming-twilio-requests
def validate_twilio_request(f):
    """Validates that incoming requests genuinely originated from Twilio"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        validator = RequestValidator(os.environ.get("TWILIO_AUTH_TOKEN"))

        request_valid = validator.validate(
            request.url, request.form,
            request.headers.get("X-TWILIO-SIGNATURE", ""))

        if request_valid:
            return f(*args, **kwargs)
        else:
            return abort(403)

    return decorated_function


@app.route("/")
def home():
    return "Hello World!"


@app.route("/gatherinfo", methods=["POST"])
@validate_twilio_request
def gather_info():
    return send_file("tasks/gather_info.json")


@app.route("/savekey", methods=["POST"])
def collect():
    memory = json.loads(request.form.get("Memory"))

    answers = memory["twilio"]["collected_data"]["collect_api_information"][
        "answers"]

    api_key = answers["api_key"]["answer"]

    message = (f"Cool, we have your api key now. It's {api_key} :) "
               f"What would you like to know?")

    return jsonify(actions=[{"say": message}, {"listen": True}])


@app.route("/currencyexchange", methods=["POST"])
@validate_twilio_request
def currency_exchange():
    return send_file("tasks/currency_exchange.json")


@app.route("/currency", methods=["POST"])
def currency_process():
    memory = json.loads(request.form.get("Memory"))

    answers = memory["twilio"]["collected_data"]["collect_currency_info"][
        "answers"]

    currency = answers["currency_type"]["answer"].lower()
    amount = answers["num_currency"]["answer"]
    message = ""

    (err, gems, coins, gold_per_gem) = convert(amount, currency)

    if err:
        message = "Error: {0}. Try again later or with a different amount.".format(
            err)
    else:
        if currency == "gems":
            message = "Exchanging {0} gems would give you {1} since 1 gem gives {2} gold".format(
                gems, coins, gold_per_gem)
        if currency == "gold":
            message = "Exchanging {0} would give you {1} gems since {2} gold gives 1 gem".format(
                coins, gems, gold_per_gem)

    return jsonify(actions=[{"say": message}])


def convert(amount, currency_type):
    api_key = False
    url = "https://api.guildwars2.com/v2/commerce/exchange"

    coins = float(amount) * 10000
    gems = int(amount)

    if currency_type == "gems":
        url += "/gems?quantity={0}".format(gems)
    if currency_type == "gold":
        url += "/coins?quantity={0}".format(coins)

    if api_key:
        url += "&access_token={0}".format(api_key)

    gw2_response = requests.get(url)

    if gw2_response.ok:
        res_data = gw2_response.json()

        gold_per_gem = float(res_data["coins_per_gem"]) / 10000

        if currency_type == "gems":
            coins = res_data["quantity"]
        if currency_type == "gold":
            gems = math.floor(res_data["quantity"])

        coins = format_gold(coins)

        return False, gems, coins, gold_per_gem
    else:
        #  gw2_response.raise_for_status()
        return gw2_response.json()["text"]


def format_gold(coins):
    silver, copper = divmod(coins, 100)
    gold, silver = divmod(silver, 100)

    return "{0} gold, {1} silver, {2} copper".format(int(gold), int(silver),
                                                     int(copper))


if __name__ == "__main__":
    app.run()
