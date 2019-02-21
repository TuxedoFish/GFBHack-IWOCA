import uuid

from datetime import datetime
import factory
import factory.fuzzy
from factory.alchemy import SQLAlchemyModelFactory

from wk_client import db, models
from wk_client.constants import APPROVED_STATE_NAME, DECLINED_STATE_NAME

BASE_TIME = datetime(2015, 4, 1, 9, 15)


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.User
        sqlalchemy_session = db.session

    username = factory.Faker('user_name')
    hashed_password = factory.Faker('password')
    account = username


class ApprovalFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Decision
        sqlalchemy_session = db.session

    decision = APPROVED_STATE_NAME
    user = factory.SubFactory(UserFactory)
    datetime = BASE_TIME

    interest_daily = 0.0005
    amount = factory.fuzzy.FuzzyChoice([1000, 5000, 15000, 25000])
    duration_days = 360
    repayment_frequency_days = 30

    fee_rate = 0
    fee_amount = 0


class DeclineFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Decision
        sqlalchemy_session = db.session

    decision = DECLINED_STATE_NAME
    user = factory.SubFactory(UserFactory)
    datetime = BASE_TIME


class DecisionFactory(ApprovalFactory):
    pass


class LoanFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.Loan
        sqlalchemy_session = db.session

    user = factory.SubFactory(UserFactory)
    start_datetime = BASE_TIME

    opening_balance = 5000.
    duration_days = 360.
    interest_daily = 0.0005

    repayment_frequency_days = 30
    repayment_amount = 458.49


class RepaymentFactory(SQLAlchemyModelFactory):
    class Meta:
        model = models.CashFlow
        sqlalchemy_session = db.session

    user = factory.SubFactory(UserFactory)
    datetime = BASE_TIME
    amount = 1000.00
    type = 1
    bank_ref = uuid.uuid4().hex


class FundingFactory(RepaymentFactory):
    amount = -5000.00
    type = 0


class FeeFactory(RepaymentFactory):
    amount = -100.00
    type = 2


class CashFlowFactory(RepaymentFactory):
    pass


def create_loan_with_funding(**kwargs):
    if 'user' in kwargs:
        user = kwargs.pop('user')
    else:
        user_params = {k.split('__')[1]: v for k, v in kwargs.items() if k.split('__')[0] == 'user'}
        user = UserFactory(**user_params)

    funding_amount = kwargs.pop('funding_amount', None)
    loan = LoanFactory(user=user, **kwargs)
    funding_amount = funding_amount or loan.opening_balance

    funding = FundingFactory(user=loan.user, datetime=loan.start_datetime, amount=-funding_amount)
    return loan, funding
