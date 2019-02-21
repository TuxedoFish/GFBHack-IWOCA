import datetime

from wk_client.constants import APPROVED_STATE_NAME, PRODUCT_NAME, MIN_LOAN_AMOUNT, DECISION_VALID_FOR_DAYS, \
    INTEREST_TYPES, REPAYMENT_TYPES
from wk_client import db


class User(db.Model):
    # TODO: Add unique constrain username?
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    hashed_password = db.Column(db.String(80))
    account = db.Column(db.String(80), unique=True, nullable=False)

    decisions = db.relationship('Decision', backref='user', lazy=True)
    loans = db.relationship('Loan', backref='user', lazy=True)
    cashflows = db.relationship('CashFlow', backref='user', lazy=True)

    def __repr__(self):
        return '<User %r>' % self.username


class Decision(db.Model):
    """
    Stores decisions.
    """
    # TODO: Add unique contrain user/datetime
    id = db.Column(db.Integer, primary_key=True)
    decision = db.Column(db.String(16), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    datetime = db.Column(db.DateTime, nullable=False)

    interest_daily = db.Column(db.Float)
    amount = db.Column(db.Float)
    duration_days = db.Column(db.Integer)
    repayment_frequency_days = db.Column(db.Integer)

    fee_rate = db.Column(db.Float)
    fee_amount = db.Column(db.Float)

    def __repr__(self):
        return '<Decision {}-{}: {}>'.format(self.user_id, self.id, self.decision)

    def to_dict(self):
        return {
            'status': 'Approved' if self.decision == APPROVED_STATE_NAME else 'Declined',
            'reference': str(self.id),
            'product': PRODUCT_NAME,
            'amount_min': MIN_LOAN_AMOUNT,
            'amount_max': self.amount,
            'duration': self.duration_days,
            'interest_type': INTEREST_TYPES['compound'],
            'interest': round((1+self.interest_daily)**365 - 1, 5) if self.interest_daily else None,
            'fee_flat': self.fee_amount,
            'fee_rate': self.fee_rate,
            'repayment_type': REPAYMENT_TYPES[1],
            'repayment_frequency': '30d',
            'valid_until': (self.datetime.date() + datetime.timedelta(DECISION_VALID_FOR_DAYS)).isoformat(),
        }


class Loan(db.Model):
    # TODO: Add unique constrain user/datetime
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False)

    opening_balance = db.Column(db.Float, nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    interest_daily = db.Column(db.Float, nullable=False)

    repayment_frequency_days = db.Column(db.Integer, nullable=False)
    repayment_amount = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '<Loan {}-{}: {}>'.format(self.user_id, self.id, self.opening_balance)


class CashFlow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    datetime = db.Column(db.DateTime, nullable=False)
    amount = db.Column(db.Float, nullable=False)  # positive - inbound, negative - outbound.
    type = db.Column(db.Integer, nullable=False)  # 0 - funding, 1 - repayment, 2 - fee
    bank_ref = db.Column(db.String(40), unique=True, nullable=False)  # UUID from bank.

    def __repr__(self):
        return 'CashFlow {}-{}: ({}, {}, {})'.format(self.user_id, self.id, self.datetime, self.amount, self.type)
