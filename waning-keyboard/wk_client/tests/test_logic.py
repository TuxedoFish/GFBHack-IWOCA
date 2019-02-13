from datetime import datetime, timedelta, date

from wk_client import db
from wk_client.logic import UserAccount, Rate
from wk_client.models import Loan, CashFlow
from wk_client.tests.conftest import AppTestCase
from wk_client.tests.factories import UserFactory, LoanFactory, RepaymentFactory, FundingFactory, \
    create_loan_with_funding
from wk_client.utils import shifted, get_repayment_amount


class TestUserAccount(AppTestCase):
    def test_true(self):
        self.assertTrue(True)

    def test_interest_rates_from_loans(self):
        base_dt = datetime(2015, 7, 15, 12, 0, 0)
        day = timedelta(days=1)

        loans = [Loan(start_datetime=shifted(days, hours, base_dt), interest_daily=interest)
            for days, hours, interest in [(0, 0, 0.001), (5, 1, 0.002), (5, 2, 0.004), (10, 1, 0.003)]]

        rates = UserAccount.interest_rates_from_loans(loans)
        self.assertListEqual(
            [r.date for r in rates],
            [base_dt.date(), base_dt.date() + 5*day, base_dt.date() + 10*day]
        )

        self.assertListEqual([r.rate for r in rates], [0.001, 0.004, 0.003])


class TestBalanceInterpolate(AppTestCase):
    def setUp(self):
        super().setUp()
        self.base_date = date(2015, 1, 1)

    def test_balance_interpolate_single_rate(self):
        rates = [Rate(self.base_date - timedelta(50), 0.003)]
        output = UserAccount.balance_interpolate(100, self.base_date, self.base_date + timedelta(60), rates)
        self.assertEqual(output, 100 * (1+0.003)**60)

    def test_balance_interpolate_no_rates(self):
        output = UserAccount.balance_interpolate(100, self.base_date, self.base_date + timedelta(60), [])
        self.assertEqual(output, 100)

    def test_balance_interpolate_future_rate(self):
        rates = [Rate(self.base_date + timedelta(70), 0.003)]
        output = UserAccount.balance_interpolate(100, self.base_date, self.base_date + timedelta(60), rates)
        self.assertEqual(output, 100)

    def test_balance_interpolate_partial_rate(self):
        rates = [Rate(self.base_date + timedelta(50), 0.003)]
        output = UserAccount.balance_interpolate(100, self.base_date, self.base_date + timedelta(60), rates)
        self.assertEqual(output, 100 * (1+0.003)**10)

    def test_balance_interpolate_edge_rate(self):
        rates = [Rate(self.base_date, 0.003), Rate(self.base_date + timedelta(1), 0.004)]
        output = UserAccount.balance_interpolate(100, self.base_date, self.base_date + timedelta(1), rates)
        self.assertEqual(output, 100 * 1.003)

    def test_balance_interpolate_multiple_rates(self):
        rates = [
            Rate(self.base_date, 0.003),
            Rate(self.base_date + timedelta(10), 0.004),
            Rate(self.base_date + timedelta(15), 0.007),
            Rate(self.base_date + timedelta(20), 0.001)
        ]

        output = UserAccount.balance_interpolate(
            200, self.base_date + timedelta(4), self.base_date+timedelta(24), rates)
        self.assertEqual(output, 200 * (1+0.003)**6 * (1+0.004)**5 * (1+0.007)**5 * (1+0.001)**4)

    def test_balance_interpolate_same_day(self):
        rates = [Rate(self.base_date - timedelta(50), 0.003)]
        output = UserAccount.balance_interpolate(100, self.base_date, self.base_date, rates)
        self.assertEqual(output, 100.)


class TestBalanceFromCashflows(AppTestCase):
    def setUp(self):
        super().setUp()

        self.base_datetime = datetime(2015, 1, 1, )
        self.base_date = self.base_datetime.date()
        self.day = timedelta(1)
        self.cashflows = [CashFlow(amount=am, datetime=self.base_datetime + td * self.day)
                          for am, td in [(-1000, 0), (200, 20), (300, 30), (250, 30), (-100, 40), (50, 40)]]
        self.rates = [Rate(self.base_date + td  * self.day, rate)
                      for rate, td in [(0.005, -5), (0.004, 0), (0., 50), (0.001, 100)]]

    def test_no_cashflows(self):
        output = UserAccount.balance_from_cashflows([], self.rates, self.base_date)
        self.assertEqual(output, 0)

    def test_before_cashflows(self):
        output = UserAccount.balance_from_cashflows(self.cashflows, self.rates, self.base_date - 5 * self.day)
        self.assertEqual(output, 0)

    def test_balance_from_cashflows(self):
        expected = [
            (-5, 0),
            (0, 1000),
            (1, 1000*1.004),
            (15, 1000*(1.004**15)),
            (20, 1000*(1.004**20) - 200),
            (21, (1000*(1.004**20) - 200)*1.004),
            (30, (1000*(1.004**20) - 200)*(1.004**10) - 550)
        ]
        for day, exp in expected:
            output = UserAccount.balance_from_cashflows(self.cashflows, self.rates, self.base_date + day * self.day)
            self.assertEqual(output, exp)

    def test_balance_from_cashflows2(self):
        day30 = (1000*(1.004**20) - 200)*(1.004**10) - 550
        expected = [
            (31, day30 * 1.004),
            (40, day30 * (1.004**10) + 50),
            (50, day30 * (1.004**20) + 50 *(1.004**10)),
            (60, day30 * (1.004**20) + 50 *(1.004**10)),
            (100, day30 * (1.004**20) + 50 *(1.004**10)),
            (101, (day30 * (1.004**20) + 50 *(1.004**10)) * 1.001)
        ]
        for day, exp in expected:
            output = UserAccount.balance_from_cashflows(self.cashflows, self.rates, self.base_date + day * self.day)
            self.assertAlmostEqual(output, exp, places=12)


class TestCashflowsByPeriod(AppTestCase):
    def setUp(self):
        super().setUp()
        self.datetime = datetime(2018, 5, 1, 15, 23)
        self.dt = self.datetime.date()

    def test_cashflows_by_period_empty(self):
        before, during, after = UserAccount.cashflows_by_period(self.dt, self.dt + timedelta(50), [])
        self.assertListEqual(before, [])
        self.assertListEqual(during, [])
        self.assertListEqual(after, [])

    def test_cashflows_by_period_one_day(self):
        cashflows = [CashFlow(datetime=self.datetime, amount=1), CashFlow(datetime=self.datetime, amount=2)]
        before, during, after = UserAccount.cashflows_by_period(self.dt - timedelta(1), self.dt, cashflows)
        self.assertListEqual(before, [])
        self.assertListEqual(during, cashflows)
        self.assertListEqual(after, [])


    def test_cashflows_by_period_one_day2(self):
        day = timedelta(days=1)
        cashflows = [CashFlow(datetime=self.datetime - 5*day , amount=1), CashFlow(datetime=self.datetime, amount=2)]
        before, during, after = UserAccount.cashflows_by_period(self.dt - timedelta(1), self.dt, cashflows)
        self.assertListEqual(before, [cashflows[0]])
        self.assertListEqual(during, [cashflows[1]])
        self.assertListEqual(after, [])

    def test_cashflows_by_period(self):
        day = timedelta(days=1)

        offsets = [-5, 0, 1, 10, 10, 15]
        amounts = [-1000, 200, 300, 250, 150, 50]
        cashflows = [CashFlow(amount=am, datetime=self.datetime+day*off) for am, off in zip(amounts, offsets)]

        before, during, after = UserAccount.cashflows_by_period(self.dt, self.dt + day * 10, cashflows)
        self.assertListEqual(before, cashflows[:2])
        self.assertListEqual(during, cashflows[2:5])
        self.assertListEqual(after, cashflows[5:])

        self.assertListEqual([c.amount for c in during], [300, 250, 150])

    def test_cashflows_by_period_dates(self):
        day = timedelta(days=1)

        offsets = [-5, 0, 1, 10, 10, 15]
        amounts = [-1000, 200, 300, 250, 150, 50]
        cashflows = [CashFlow(amount=am, datetime=self.dt+day*off) for am, off in zip(amounts, offsets)]

        before, during, after = UserAccount.cashflows_by_period(self.dt, self.dt + day * 10, cashflows)
        self.assertListEqual(before, cashflows[:2])
        self.assertListEqual(during, cashflows[2:5])
        self.assertListEqual(after, cashflows[5:])

        self.assertListEqual([c.amount for c in during], [300, 250, 150])

    def test_cashflows_by_period_mixtypes(self):
        day = timedelta(days=1)

        offsets = [-5, 0, 1, 10, 10, 15]
        amounts = [-1000, 200, 300, 250, 150, 50]
        datetimes = [
            self.datetime + offsets[0]*day,
            self.datetime + offsets[1]*day,
            self.dt + offsets[2]*day,
            self.datetime + offsets[3]*day,
            self.dt + offsets[4]*day,
            self.datetime + offsets[5]*day,

        ]

        cashflows = [CashFlow(amount=am, datetime=dt) for am, dt in zip(amounts, datetimes)]

        before, during, after = UserAccount.cashflows_by_period(self.dt, self.dt + day * 10, cashflows)
        self.assertListEqual(before, cashflows[:2])
        self.assertListEqual(during, cashflows[2:5])
        self.assertListEqual(after, cashflows[5:])

        self.assertListEqual([c.amount for c in during], [300, 250, 150])


class TestRepaymentSchedules(AppTestCase):
    def setUp(self):
        super().setUp()
        self.datetime = datetime(2018, 5, 1, 15, 23)
        self.dt = self.datetime.date()

    def test_simple_loan_schedule(self):
        user = UserFactory()
        loan = LoanFactory(
            user=user,
            opening_balance=7500.,
            duration_days=360,
            repayment_frequency_days=30,
            repayment_amount=690.00,
            interest_daily=0.0005,
            start_datetime = self.datetime,
        )
        db.session.commit()
        ua = UserAccount(user.id)

        final_payment = 664.79
        expected_schedule = {self.dt + timedelta(i*30): 690. for i in range(1, 12)}
        expected_schedule[self.dt + timedelta(12*30)] = final_payment
        self.assertDictEqual(expected_schedule, ua.repayment_schedule_for_loan(loan))

    def test_get_repayment_amount_exact(self):
        user = UserFactory()
        loan_size = 7500.
        rep_frequency = 10.
        duration = 180
        interest_daily = 0.001

        rep_size, _ = get_repayment_amount(loan_size, duration, rep_frequency, interest_daily)

        cashflows = [FundingFactory(user=user, amount=-7500., datetime=self.datetime)]
        cashflows += [
            RepaymentFactory(user=user, amount=rep_size, datetime=self.datetime + timedelta(i*10))
            for i in range(1, 19)
        ]

        def balance(as_of):
            return UserAccount.balance_from_cashflows(cashflows, [Rate(self.dt, interest_daily)], as_of)

        self.assertAlmostEqual(balance(self.dt+timedelta(180)), 0)
        self.assertTrue(balance(self.dt+timedelta(179)) > 1)

    def test_repayment_schedule(self):
        loan, _ = create_loan_with_funding(
            opening_balance=7500.,
            start_datetime=self.datetime,
            duration_days=360,
            repayment_frequency_days=30,
            repayment_amount=690.00,
            interest_daily=0.0005,
            )

        db.session.commit()
        ua = UserAccount(loan.user.id)

        rep_schedule = ua.repayment_schedule_for_date(self.datetime.date())
        final_date = max(date for date in rep_schedule)
        final_amount = rep_schedule[final_date]
        del rep_schedule[final_date]
        expected = {self.datetime.date() + timedelta(d): 690. for d in range(30, 359, 30)}
        self.assertEqual(rep_schedule, expected)

        cf = [CashFlow(amount=a, datetime=k, type=1) for k, a in expected.items()]
        remnant = ua.balance_from_cashflows(ua.cashflows + cf, ua.interest_rates_from_loans(ua.loans), final_date)
        self.assertEqual(final_amount, round(remnant, 2))
