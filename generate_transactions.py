"""A Script to generate random transactions for simulating a bank in testing.
"""
import csv
import datetime
import json

import numpy
import os.path
import random
import sys
import uuid

TEST_ACCOUNTS = [
    "9f0117cbaf55407d97709e409b0def4a",
    "aff9e079d56043d1a40a671dcb0270df",
    "469d5c23bd6f49558eebdc99d4c65665",
    "e813a98672084284801af9df41625508",
]
OUR_ACCOUNT = "782cab3857fd4f34be101d63358fd6"

TRANSACTION_FILENAME = "transactions.csv"

SHAPE = 2
SCALE = 1000
REF_TIME = datetime.datetime(2019, 1, 5)


def generate_random_amount():
    amount = numpy.random.gamma(SHAPE, SCALE)
    return round(amount, 2)


def time_now():
    """Accelerated time
    """
    with open("clock.dat", "r") as r:
        prev_time = datetime.datetime.fromisoformat(
            r.read()
        )

    # TODO: Replace with exponential distr.?
    offset = datetime.timedelta(
        minutes=random.randint(0, 30),
        seconds=random.randint(0, 3600),
    )
    new_time = prev_time + offset

    with open("clock.dat", "w") as w:
        w.write(new_time.isoformat())
    return new_time


def generate_outbound_transaction(data, write=True
):
    transaction = {
        "datetime": time_now().isoformat(),
        "account_to": data['account_to'],
        "account_from": data['account'],
        "amount": data['amount'],
        "reference": uuid.uuid4().hex,
    }

    if write:
        write_transactions([transaction])
    return json.dumps(transaction)


def generate_inbound_transaction():
    acc = random.choice(TEST_ACCOUNTS)
    amount = generate_random_amount()
    time = time_now()
    return {
        "datetime": time.isoformat(),
        "account_to": OUR_ACCOUNT,
        "account_from": acc,
        "amount": amount,
        "reference": uuid.uuid4().hex,
    }


def write_transactions(transactions):
    filename = TRANSACTION_FILENAME
    file_exists = os.path.isfile(filename)

    with open(filename, "a") as f:
        fieldnames = [
            "reference",
            "datetime",
            "account_from",
            "account_to",
            "amount",
        ]
        writer = csv.DictWriter(f, fieldnames)
        if not file_exists:
            writer.writeheader()

        for transaction in transactions:
            print(
                transaction["datetime"],
                transaction["account_from"][:6],
                transaction["amount"],
            )
            writer.writerow(transaction)


if __name__ == "__main__":
    n_records = int(sys.argv[1])
    print("Generating {} cashflows".format(n_records))
    transactions = [
        generate_inbound_transaction()
        for _ in range(n_records)
    ]
    write_transactions(transactions)
