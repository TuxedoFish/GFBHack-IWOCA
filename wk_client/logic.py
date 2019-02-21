import bisect
import datetime
from collections import namedtuple

import dateutil

from wk_client import models, bank
from wk_client.constants import APPROVED_STATE_NAME, DECLINED_STATE_NAME, FUNDING_TYPE, DECISION_VALID_FOR_DAYS, \
    EXAMPLE_DOC_REQUIREMENTS
from wk_client.models import CashFlow, Loan
from wk_client.utils import get_repayment_amount, get_date

Rate = namedtuple('rate', ['date', 'rate'])


class UserAccount(object):
    def __init__(self, user_id=None):
        self.user = models.User.query.get(user_id)
        self.loans = sorted(list(self.user.loans), key=lambda x: x.start_datetime)
        self.cashflows = sorted(list(self.user.cashflows), key=lambda x: (x.datetime, x.id))
        self.decisions = sorted(list(self.user.decisions), key=lambda x: (x.datetime, x.id))

    def get_active_decision(self, dt):
        for d in self.decisions[::-1]:
            if dt - datetime.timedelta(days=DECISION_VALID_FOR_DAYS) < d.datetime <= dt:
                return d

    def add_funding(self, amount):
        cashflow = bank.send_cash(amount=amount, account_to=self.user.account)
        return self.add_cashflow(-1 * cashflow['amount'], cashflow['timestamp'], FUNDING_TYPE, ref=cashflow['bank_ref'])

    def add_cashflow(self, amount, dt, cashflow_type, ref=None):
        """
        Creates CashFlow
        Args:
            amount:
            dt:
            cashflow_type:
            ref:

        Returns:

        """
        if ref is None:
            ref = 'Internal'
        cf = models.CashFlow(user=self.user, amount=amount, datetime=dt, type=cashflow_type, bank_ref=ref)
        models.db.session.add(cf)
        models.db.session.commit()

        self.cashflows = sorted(self.cashflows + [cf], key=lambda x: x.datetime)
        return cf

    def create_loan(self, start_datetime, opening_balance,
                    duration_days=360, interest_daily=0.0005, repayment_frequency_days=30):
        """
        Creates Loan
        Args:
            start_datetime:
            opening_balance:
            duration_days:
            interest_daily:
            repayment_frequency_days:

        Returns:

        """
        rep_am, _ = get_repayment_amount(opening_balance, duration_days, repayment_frequency_days, interest_daily)

        loan = models.Loan(user=self.user, start_datetime=start_datetime, opening_balance=opening_balance,
                    duration_days=duration_days, interest_daily=interest_daily,
                    repayment_frequency_days=repayment_frequency_days, repayment_amount=round(rep_am + 0.005, 2))

        models.db.session.add(loan)
        models.db.session.commit()

        # TODO: Bisect for insertion in sorted list.
        self.loans = sorted(self.loans + [loan], key=lambda x: x.start_datetime)
        return loan

    @staticmethod
    def interest_rates_from_loans(loans):
        rate_dict = {get_date(loan.start_datetime): loan.interest_daily for loan in loans}
        return sorted([Rate(date, rate) for date, rate in rate_dict.items()], key=lambda x: x.date)

    @staticmethod
    def balance_interpolate(start_balance, start_date, end_date, rates):
        """

        Args:
            start_balance (float):
            start_date:
            end_date:
            rates (list of Rates):

        Returns:

        """
        rates = [r for r in rates if r.date < end_date] + [Rate(end_date, 0)]
        for prev_rate, next_rate in zip(rates[:-1], rates[1:]):
            dur = max(0, (next_rate.date - max(prev_rate.date, start_date)).days)
            start_balance *= (1 + prev_rate.rate)**dur
        return start_balance

    def balance(self, as_of):
        rates = self.interest_rates_from_loans(self.loans)
        return UserAccount.balance_from_cashflows(self.cashflows, rates, as_of)

    @staticmethod
    def balance_from_cashflows(cashflows, rates, as_of):
        """
        Computes balance on the as_of date, assuming rate is constant and cashflows are all the cashflows.
        Args:
            cashflows: List of cashflows. (Fake cashflows can be used to compute partial results.
            rates (list of Rates):
            as_of: The date to give the answer for.

        Returns:
            (float) Balance on as of day.
        """
        cashflows = [c for c in cashflows if get_date(c.datetime) <= as_of]  # Cashflows on the date included.
        if not cashflows:
            return 0

        date = get_date(cashflows[0].datetime)

        current_balance = 0

        next_cashflow = cashflows.pop(0)
        while next_cashflow:
            while get_date(next_cashflow.datetime) == date:
                current_balance -= next_cashflow.amount
                try:
                    next_cashflow = cashflows.pop(0)
                    next_date = get_date(next_cashflow.datetime)
                except IndexError:
                    next_cashflow = None
                    next_date = as_of
                    break
            current_balance = UserAccount.balance_interpolate(current_balance, date, next_date, rates)
            date = next_date

        return current_balance

    def repayment_schedule_for_loan(self, loan):
        fake_cashflows = [CashFlow(datetime=loan.start_datetime, amount=-1 * loan.opening_balance, type=0)]
        rates = [Rate(loan.start_datetime.date(), loan.interest_daily)]
        as_of = loan.start_datetime.date()
        return self.repayment_schedule2(loan, fake_cashflows, rates, as_of)

    def repayment_schedule_for_date(self, as_of):
        real_cashflows = [c for c in self.cashflows if get_date(c.datetime) <= as_of]
        loans = [l for l in self.loans if l.start_datetime.date() <= as_of]
        if loans:
            loan = loans[-1]
        else:
            # cashflows before loan are bad
            return {}

        rates = self.interest_rates_from_loans(loans)
        return self.repayment_schedule2(loan, real_cashflows, rates, as_of)

    @staticmethod
    def cashflows_by_period(period_start, period_end, cashflows):
        """
        Splits cashflows by period into 3: before start of period, during period and after end of period.
        Period is a date, inside period is if date in (period_start, period_end].
        """
        assert period_end > period_start
        dates = [get_date(c.datetime) for c in cashflows]

        start = bisect.bisect_right(dates, period_start)
        end = bisect.bisect_right(dates, period_end)

        return cashflows[:start], cashflows[start: end], cashflows[end:]

    def repayment_schedule2(self, loan, cashflows, rates, as_of):
        schedule = []

        repayment_frequency = datetime.timedelta(loan.repayment_frequency_days)
        start_date = get_date(loan.start_datetime)
        min_repayment = loan.repayment_amount

        prev_date = start_date
        cur_date = prev_date + repayment_frequency

        while cur_date < as_of:
            prev_date = cur_date
            cur_date += repayment_frequency
        balance = self.balance_from_cashflows(cashflows, rates, prev_date)
        #what if overdue? should really be falling due now. Do future cashflows make sense in such case though?

        while balance > 0.01:
            past, present, future = self.cashflows_by_period(prev_date, cur_date, cashflows)
            paid_this_period = sum(c.amount for c in present)
            balance = self.balance_from_cashflows(
                [CashFlow(amount=-balance, datetime=prev_date)] + present,
                rates,
                cur_date
            )
            repayment = round(min(max(min_repayment - paid_this_period, 0), balance), 2)
            balance -= repayment

            schedule += present
            if repayment > 0:
                schedule += [CashFlow(amount=repayment, datetime=cur_date)]

            cashflows = future
            prev_date = cur_date
            cur_date += repayment_frequency

        dates = [dt for dt in [get_date(c.datetime) for c in schedule] if dt >= as_of]
        return {date: sum(c.amount for c in schedule if get_date(c.datetime) == date) for date in dates}

    def payment_due(self, loan, cashflows, as_of):
        """
        Returns payment due, considering min repayment and any cashflows. Doesn't consider balance.
        Args:
            loan:
            cashflows:
            as_of:

        Returns:

        """
        min_repayment = loan.repayment_amount
        unpaid_amount = 0
        prev_date = get_date(loan.start_datetime)
        repayment_frequency = datetime.timedelta(loan.repayment_frequency_days)
        cur_date = prev_date + repayment_frequency
        while cur_date < as_of:
            past, present, future = self.cashflows_by_period(prev_date, cur_date, cashflows)
            paid_this_period = sum(c.amount for c in present)

            unpaid_amount += min_repayment - paid_this_period
            unpaid_amount = max(0, unpaid_amount)

            prev_date = cur_date
            cur_date += repayment_frequency
            cashflows = future

        if cur_date == as_of:
            return unpaid_amount + min_repayment  # still need to limit by balance
        else:
            return unpaid_amount


def approve_user(user, dt, amount, interest_rate, fee_rate=0, fee_amount=0):
    decision = models.Decision(
        user=user,
        decision=APPROVED_STATE_NAME,
        datetime=dt,
        amount=amount,
        interest_daily=interest_rate,
        fee_rate=fee_rate,
        fee_amount=fee_amount,
        duration_days=360,
        repayment_frequency_days=30
    )

    models.db.session.add(decision)
    models.db.session.commit()
    return decision


def decline_user(user, dt):
    decision = models.Decision(user=user, decision=DECLINED_STATE_NAME, datetime=dt)
    models.db.session.add(decision)
    models.db.session.commit()
    return decision


class DecisionParams:
    def __init__(self, approved, params=None):
        self.approved = approved
        self.params = params or {}


def get_requirements(data):
    return EXAMPLE_DOC_REQUIREMENTS


def check_requirements(data, requirements):
    if data is None:
        data = {}
    for k in requirements:
        if not data.get(k):
            return False
    return True



def evaluate_decision(data):
    dob = dateutil.parser.parse(data['basic_questions']['date_of_birth'])
    if dob.year < 1989:
        params = {'amount': 5000, 'interest_rate': 0.0005, 'fee_amount': 0, 'fee_rate': 0}
        return DecisionParams(approved=True, params=params)
    else:
        return DecisionParams(approved=False)

