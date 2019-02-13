from wk_client import logic, app
from wk_client.constants import FEE_TYPE, INTEREST_TYPES, REPAYMENT_TYPES, DECLINED_STATE_NAME
from wk_client.constants import MIN_LOAN_AMOUNT, MAX_LOAN_AMOUNT
from wk_client.logic import approve_user, decline_user
from wk_client.request_utils import time_now
from wk_client.utils import get_date


def get_product_data():
    # TODO: The product details of this endpoint should be tied in to the config, somehow, so that the actual product would also follow it.
    return {'standard': {
        'amount_min': MIN_LOAN_AMOUNT,
        'amount_max': MAX_LOAN_AMOUNT,
        'amount_representative': 3000,
        'duration_min': 360,
        'duration_max': 365,
        'duration_representative': 360,
        'interest_type': INTEREST_TYPES['compound'],
        'interest_min': 0.02,
        'interest_max': 0.1,
        'interest_representative': 0.05,
        'fee_flat': 100,
        'fee_rate_min': 0.,
        'fee_rate_max': 0.,
        'apr': 0.20,
        'repayment_type': REPAYMENT_TYPES[2],
        'repayment_frequency': '30d'  # Can repayments fall on weekends?
    }}


def get_decision(user, data):
    requirements = logic.get_requirements(data)
    if not logic.check_requirements(data, requirements):
        return {'requirements': requirements}
    else:
        data['time_now'] = time_now()
        try:
            raw_decision = logic.evaluate_decision(data)
        except Exception as e:
            app.logger.error('Unexpected Error evaluating decision. Rejected. %s, %s', e, data)
            decision = decline_user(user, time_now())
        else:
            if raw_decision.approved:
                decision = approve_user(user, time_now(), **raw_decision.params)
            else:
                decision = decline_user(user, time_now())
        return {'decision': decision.to_dict(), 'requirements': requirements}


def request_funding(user_account, approval_id, amount, dt):
    active_decision = user_account.get_active_decision(dt)
    if (active_decision is None
            or approval_id != active_decision.id
            or active_decision.decision == DECLINED_STATE_NAME):
        return None, 'Invalid Decision'

    cur_balance = user_account.balance(get_date(dt))
    if MIN_LOAN_AMOUNT <= cur_balance + amount <= active_decision.amount:
        user_account.add_funding(amount)

        fee = active_decision.fee_rate * amount + active_decision.fee_amount
        if fee:
            user_account.add_cashflow(-1*fee, dt, cashflow_type=FEE_TYPE, ref='Internal')

        loan = user_account.create_loan(dt, cur_balance + amount + fee,
                       duration_days=active_decision.duration_days,
                       interest_daily=active_decision.interest_daily,
                       repayment_frequency_days=active_decision.repayment_frequency_days)
        return loan, None
    else:
        return None, 'Invalid Amount'
