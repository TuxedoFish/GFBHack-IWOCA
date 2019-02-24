import csv
import json
from json import JSONDecodeError
from flask import current_app as app

import dateutil.parser
import requests
import logging

from wk_client import db
from wk_client.constants import REPAYMENT_TYPE
from wk_client.models import User, CashFlow
from wk_client.settings import BANK_HOST, BANK_PASSWORD, BANK_PORT, BANK_USERNAME, BANK_ACCOUNT

from generate_transactions import OUR_ACCOUNT, TRANSACTION_FILENAME


def send_cash(amount, account_to):
    # TODO: write tests.
    """
    Send a cashflow (funding) from institution to customer.

    Returns:
        dict:
            'amount': Amount sent (as confirmed by bank)
            'timestamp': Timestamp of cashflow (as confirmed by bank)
    """
    app.logger.info('Sending Transaction: %s, %s', amount, account_to)
    trans = _send_transaction(amount, account_to)
    if not trans:
        app.logger.error('Transaction Not Sent %s, %s', amount, account_to)
        raise ValueError('Couldn\'t send transaction')  # TODO: Use a better.
    return {
        'amount': float(trans['amount']),
        'timestamp': dateutil.parser.parse(trans['datetime']),
        'bank_ref': trans['reference']
    }

def create_fake_response(data):
    from requests.models import Response
    resp = Response()
    resp._content = data
    resp.status_code = 200
    return resp

def _send_fake_transaction_request(data):
    """Mock Bank API for internal testing
    """
    from generate_transactions import generate_outbound_transaction
    data = generate_outbound_transaction(data, write=True)
    return create_fake_response(data)


def _send_real_transaction_request(data):
    url = '{}:{}/transaction'.format(BANK_HOST, BANK_PORT)
    return requests.post(url, data=data, auth=(BANK_USERNAME, BANK_PASSWORD), verify=False)

def _send_transaction_request(data):
    if app.debug:
        return _send_fake_transaction_request(data)
    else:
        return _send_real_transaction_request(data)


def _send_transaction(amount, account_to):
    data = {'account': BANK_ACCOUNT, 'account_to': account_to, 'amount': amount}
    response = _send_transaction_request(data)
    logging.warning('transaction: request {}, response {}'.format(data, response))
    if response.status_code == 200:
        return json.loads(response.content)
    else:
        app.logger.error('Error sending transaction: %s, %s. \n %s', amount, account_to, response.content.decode())


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
    try:
        response = requests.get(
            '{}:{}/statement'.format(BANK_HOST, BANK_PORT),
            auth=(BANK_USERNAME, BANK_PASSWORD),
            data={'account': BANK_ACCOUNT},
            verify=False)
        return json.loads(response.content)
    except (requests.exceptions.ConnectionError, JSONDecodeError)as e:
        app.logger.error('Could not download transactions from bank. Exception: {}'.format(e))
        return []


def _retrieve_all_cashflows():
    if app.debug:
        cashflows = _retrieve_fake_cashflows()
    else:
        cashflows = _retrieve_real_cashflows()
    return cashflows


def load_new_inbound_cashflows():
    """Loads new inbound cashflows from the bank. Loads up the bank statement for our account
    and filters those cashflows that were already stored.

    If the user cannot be identified from the account, an error is logged, but the cashflow is not returned.

    Returns: list of new cashflows.
    """

    cashflows = _retrieve_all_cashflows()
    existing_cashflows = [cf[0] for cf in CashFlow.query.with_entities(CashFlow.bank_ref).all()]
    user_map = UserMap()
    missing_cashflows = []
    for cashflow in cashflows:
        if cashflow['reference'] not in existing_cashflows and cashflow['in'] > 0:
            try:
                uid = user_map[cashflow['account']]
            except KeyError:
                app.logger.error('Couldnt identify user account for cashflow %s', cashflow)
            else:
                missing_cashflows.append({
                    'amount': float(cashflow['in']),
                    'timestamp': dateutil.parser.parse(cashflow['datetime']),
                    'bank_ref': cashflow['reference'],
                    'user_id': uid
                    })
    return missing_cashflows


def fetch_cashflows():
    """Stores to database cashflows that weren't stored previously.
    """
    new_cashflows = load_new_inbound_cashflows()
    for cashflow in new_cashflows:
        cf = CashFlow(
            user_id=cashflow['user_id'],
            amount=cashflow['amount'],
            datetime=cashflow['timestamp'],
            type=REPAYMENT_TYPE,
            bank_ref = cashflow['bank_ref']
        )
        db.session.add(cf)
    app.logger.info('Retrieved {} new cashflows'.format(len(new_cashflows)))
    db.session.commit()


def get_time_from_bank():
    """Requests current bank from the bank server. This is not the way to handle time of requests,
    but could be useful for e.g. tracking the game progress."""
    response = requests.get(
        '{}:{}/time_now'.format(BANK_HOST, BANK_PORT),
        auth=(BANK_USERNAME, BANK_PASSWORD),
        data={'account': BANK_ACCOUNT},
        verify=False)
    return response
