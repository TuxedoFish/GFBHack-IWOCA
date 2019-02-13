import csv
import json

import dateutil.parser
import requests

from wk_client import app
from wk_client.models import User
from wk_client.settings import BANK_HOST, BANK_PASSWORD, BANK_PORT, BANK_USERNAME, BANK_ACCOUNT

from generate_transactions import TEST_ACCOUNTS, OUR_ACCOUNT, TRANSACTION_FILENAME


def send_cash(amount, account):
    # TODO: write tests.
    """
    Send a cashflow (funding) from institution to customer.
    Args:
        amount: Amount
        account: Customers account

    Returns:
        dict:
            'amount': Amount sent (as confirmed by bank)
            'timestamp': Timestamp of cashflow (as confirmed by bank)
    """
    app.logger.info('Sending Transaction: %s, %s', amount, account)
    if app.debug:
        trans = _send_fake_transaction(amount, account)
    else:
        trans = _send_real_transaction(amount, account)
    if not trans:
        app.logger.error('Transaction Not Sent %s, %s', amount, account)
        raise RuntimeError('Couldn\'t send transaction')  # TODO: Graceful handle?
    return {
        'amount': float(trans['amount']),
        'timestamp': dateutil.parser.parse(trans['datetime']),
        'bank_ref': trans['reference']
    }


class UserMap(dict):
    """Map bank accounts to users"""
    def __init__(self):
        all_users = User.query.with_entities(User.account, User.id).all()
        self.update(all_users)

def _retrieve_fake_cashflows():
    """Retrieve cashflows from local bank

    """
    #TODO: Testing.
    with open(TRANSACTION_FILENAME,'r') as f:
        reader = csv.DictReader(f)

        def inbound_transaction(tr):
            return [{
                'in': float(tr['amount']),
                'out': 0,
                'datetime':  dateutil.parser.parse(tr['timestamp']),
                'reference': tr['bank_ref'],
                'account': tr['account_from'],
            }]
        def outbound_transaction(tr):
            return [{
                'in': 0,
                'out': float(tr['amount']),
                'datetime': dateutil.parser.parse(tr['timestamp']),
                'reference': tr['bank_ref'],
                'account': tr['account_to'],
            }]

        transactions = [inbound_transaction(tr)
                        if tr['account_to'] == OUR_ACCOUNT
                        else outbound_transaction(tr)
                        for tr in reader]

    return transactions


def _retrieve_real_cashflows():
    """Retrieve cashflows from bank server"""
    #TODO: Testing
    response = requests.get(
        '{}:{}/statement'.format(BANK_HOST, BANK_PORT),
        auth=(BANK_USERNAME, BANK_PASSWORD),
        data={'account': BANK_ACCOUNT})
    try:
        return json.loads(response.content)
    except ConnectionError:
        app.logger.error('Could not download transactions from bank')
        return []


def _send_fake_transaction(amount, account):
    """Mock Bank API for internal testing
    """
    from generate_transactions import generate_outbound_transaction
    return generate_outbound_transaction(amount, account, write=True)


def _send_real_transaction(amount, account):
    response =  requests.post('{}:{}/transaction'.format(BANK_HOST, BANK_PORT),
        data={'account': BANK_ACCOUNT, 'account_to': account, 'amount': amount}, auth=(BANK_USERNAME, BANK_PASSWORD)
    )
    if response.status_code == 200:
        return json.loads(response.content)
    else:
        app.logger.error('Error sending transaction: %s, %s. \n %s', amount, account, response.content.decode())


def get_time_from_bank():
    """Requests current bank from the bank server. This is not the way to handle time of requests,
    but could be useful for e.g. tracking the game progress."""
    response = requests.get(
        '{}:{}/time_now'.format(BANK_HOST, BANK_PORT),
        auth=(BANK_USERNAME, BANK_PASSWORD),
        data={'account': BANK_ACCOUNT})
    return response
