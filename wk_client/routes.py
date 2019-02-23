import json
import logging

from flask import Blueprint, request, g
from werkzeug.exceptions import BadRequest

from wk_client import auth, endpoints
from wk_client.auth_utils import create_user
from wk_client.logic import UserAccount
from wk_client.request_utils import time_now
from wk_client.settings import BANK_ACCOUNT
from wk_client.utils import get_date

bp = Blueprint('routes', __name__)

logging.basicConfig(level=logging.DEBUG, filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

@bp.route('/')
@bp.route('/index')
def index():
    return "Hello, World!"


@bp.route('/get_info', methods=('GET',))
def get_info():
    return json.dumps(endpoints.get_product_data())


@bp.route('/register', methods=('POST',))
def register():
    if request.method == 'POST':
        data = request.get_json()
        try:
            username = data['username']
            password = data['password']
            account = data['bank_account']
        except KeyError:
            raise BadRequest()
        user = create_user(username, password, account)
        return json.dumps(user.username)


@bp.route('/test_login', methods=('GET', 'POST'))
@auth.login_required
def test_login():
    return json.dumps('Hello {}'.format(auth.username()))


@bp.route('/get_decision', methods=('GET', 'POST'))
@auth.login_required
def get_decision():
    logging.warning("Getting decision for ~ ")
    logging.warning(request.get_json())
    if request.method == 'GET':
        return json.dumps(endpoints.get_decision(g.user, None))
    elif request.method == 'POST':
        data = request.get_json()
        return json.dumps(endpoints.get_decision(g.user, data))


@bp.route('/request_funding', methods=('POST',))
@auth.login_required
def request_funding():
    """
    Request funding - Check that approval in question is still the active one. Balance is 0? (flexibiltiy?
    Returns:

    """
    data = request.get_json()
    amount = data['amount']
    approval_id = data['approval_reference']
    dt = time_now()
    user_account = UserAccount(g.user.id)
    funding, error = endpoints.request_funding(
        user_account,
        approval_id=approval_id,
        amount=amount,
        dt=dt
    )
    if error:
        raise BadRequest(error)
    else:
        schedule = {
            k.isoformat(): v for k, v in user_account.repayment_schedule_for_loan(funding).items()
        }

        return json.dumps({
            'funding_reference': funding.id,
            'repayment_account': BANK_ACCOUNT,
            'repayment_schedule': schedule
        })


@bp.route('/get_schedule', methods=('GET',))
@auth.login_required
def get_schedule():
    user_account = UserAccount(g.user.id)
    as_of = get_date(time_now())
    balance = user_account.balance(as_of)
    schedule = user_account.repayment_schedule_for_date(as_of)
    return json.dumps({
        'balance': balance,
        'schedule': {k.isoformat(): v for k, v in schedule.items()}
    })
