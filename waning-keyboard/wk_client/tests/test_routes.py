import json
from datetime import datetime, timedelta
from unittest import mock


from wk_client.auth_utils import create_user
from wk_client.constants import APPROVED_STATE_NAME, MIN_LOAN_AMOUNT, PRODUCT_NAME, DECLINED_STATE_NAME
from wk_client.logic import DecisionParams
from wk_client.models import User, Decision, Loan, CashFlow
from wk_client.settings import BANK_ACCOUNT
from wk_client.tests.conftest import AppTestCase, open_with_auth, post_json
from wk_client.tests.factories import DeclineFactory, ApprovalFactory, create_loan_with_funding

EXAMPLE_REQUIREMENTS = ['basic_questions', 'credit_report', 'company_report']


class TestHelloWorld(AppTestCase):
    def test_hello_world(self):
        rv = self.client.get('/')
        assert b'Hello, World!' in rv.data


class TestLogin(AppTestCase):
    def setUp(self):
        super(TestLogin, self).setUp()
        create_user('foo', 'bar', 'baz')

    def test_login_fails_wrong_username(self):
        rv = open_with_auth(self.client, '/test_login', 'get', b'foo1', b'bar')
        assert b'Hello foo' not in rv.data

    def test_login_fails_wrong_password(self):
        rv = open_with_auth(self.client, '/test_login', 'get', b'foo', b'bar1')
        assert b'Hello foo' not in rv.data

    def test_login_successful(self):
        rv = open_with_auth(self.client, '/test_login', 'get', b'foo', b'bar')
        assert b'Hello foo' in rv.data

    def test_login_successful_post(self):
        rv = open_with_auth(self.client, '/test_login', 'post', b'foo', b'bar')
        assert b'Hello foo' in rv.data

    def test_login_fails_post(self):
        rv = open_with_auth(self.client, '/test_login', 'post', b'foo', b'bar1')
        assert b'Hello foo' not in rv.data


class TestRegister(AppTestCase):
    def test_register_new_user(self):
        payload = {'username': 'new_user', 'password': 'bar', 'bank_account': 'abcdef'}
        rv = post_json(self.client, '/register', data=payload)
        assert b'new_user' in rv.data
        assert User.query.filter_by(username='new_user').scalar()

    def test_register_existing_user_fails(self):
        params = ('existing_user', 'bar', 'abcdef')
        create_user(*params)
        payload = {k: v for k, v in zip(['username', 'password', 'bank_account'], params)}
        rv = post_json(self.client, '/register', data=payload)
        assert b'existing_user' not in rv.data
        assert rv.status == '400 BAD REQUEST'
        assert User.query.filter_by(username='existing_user').count() == 1

    def test_register_incomplete_details_fails(self):
        payload = {'username': 'incomplete_user', 'password': 'bar'}
        rv = post_json(self.client, '/register', payload)
        assert b'incomplete_user' not in rv.data
        assert rv.status == '400 BAD REQUEST'
        assert User.query.filter_by(username='incomplete_user').count() == 0


class TestGetInfo(AppTestCase):
    @mock.patch('wk_client.endpoints.get_product_data')
    def test_return_product_data(self, mock_get_product_data):
        mock_product = {'foo': {'bar': 'baz'}}
        mock_get_product_data.return_value = mock_product
        rv = self.client.get('/get_info')
        assert rv.data.decode() == json.dumps(mock_product)

    def test_get_info(self):
        # TODO: Replace with schema validation test.
        rv = self.client.get('/get_info')
        assert isinstance(json.loads(rv.data.decode()), dict)


class TestGetDecisionGet(AppTestCase):
    @mock.patch('wk_client.logic.get_requirements')
    def test_get_decision_get_returns_requirements(self, mock_get_requirements):
        create_user('user1', 'pass1', 'acc1')
        mock_requirements = EXAMPLE_REQUIREMENTS
        mock_get_requirements.return_value = mock_requirements
        rv = open_with_auth(self.client, '/get_decision', 'get', b'user1', b'pass1')
        assert json.loads(rv.data) == {'requirements': mock_requirements}

    @mock.patch('wk_client.logic.get_requirements')
    def test_get_decision_get_requires_authentication(self, mock_get_requirements):
        mock_requirements = EXAMPLE_REQUIREMENTS
        mock_get_requirements.return_value = mock_requirements
        rv = self.client.get('/get_decision')
        assert '200' not in rv.status
        assert b'applicant' not in rv.data


class TestGetDecisionPost(AppTestCase):
    def setUp(self):
        super(TestGetDecisionPost, self).setUp()
        self.test_user = create_user('user2', 'pass2', 'acc2')

    @mock.patch('wk_client.logic.check_requirements')
    @mock.patch('wk_client.logic.get_requirements')
    def test_get_decision_post_no_decision(self, mock_get_requirements, mock_check_requirements):
        mock_check_requirements.return_value = False
        mock_get_requirements.return_value = EXAMPLE_REQUIREMENTS
        rv = post_json(self.client, '/get_decision', data={}, username=b'user2', password=b'pass2')
        assert rv.status == '200 OK'
        assert json.loads(rv.data) == {'requirements': EXAMPLE_REQUIREMENTS}

    @mock.patch('wk_client.logic.evaluate_decision')
    @mock.patch('wk_client.logic.check_requirements')
    @mock.patch('wk_client.logic.get_requirements')
    def test_get_decision_approve(self, mock_get_requirements, mock_check_requirements, mock_evaluate_decision):
        mock_check_requirements.return_value = True
        mock_get_requirements.return_value = EXAMPLE_REQUIREMENTS
        mock_evaluate_decision.return_value = DecisionParams(
            approved=True,
            params={'amount': 5000, 'interest_rate': 0.0005, 'fee_amount': 0, 'fee_rate': 0}
        )
        tstamp = datetime(2018, 5, 4, 14, 3, 12)
        rv = post_json(self.client, '/get_decision', data={}, username=b'user2', password=b'pass2', timestamp=tstamp)
        assert rv.status == '200 OK'
        assert Decision.query.filter_by(user_id=self.test_user.id).count() == 1

        decision = Decision.query.filter_by(user_id=self.test_user.id)[0]
        expected_object = {
            'decision': APPROVED_STATE_NAME,
            'datetime': tstamp,
            'interest_daily': 0.0005,
            'amount': 5000.,
            'duration_days': 360,
            'repayment_frequency_days': 30,
            'fee_rate': 0,
            'fee_amount': 0
        }

        for k, v in expected_object.items():
            assert getattr(decision, k) == v

        expected_presentation = decision.to_dict()
        assert json.loads(rv.data) == {'requirements': EXAMPLE_REQUIREMENTS, 'decision': expected_presentation}

    @mock.patch('wk_client.logic.evaluate_decision')
    @mock.patch('wk_client.logic.check_requirements')
    @mock.patch('wk_client.logic.get_requirements')
    def test_get_decision_decline(self, mock_get_requirements, mock_check_requirements, mock_evaluate_decision):
        mock_check_requirements.return_value = True
        mock_get_requirements.return_value = EXAMPLE_REQUIREMENTS
        mock_evaluate_decision.return_value = DecisionParams(
            approved=False,
        )

        tstamp = datetime(2018, 5, 4, 14, 3, 15)
        rv = post_json(self.client, '/get_decision', data={}, username=b'user2', password=b'pass2', timestamp=tstamp)
        assert rv.status == '200 OK'
        assert Decision.query.filter_by(user_id=self.test_user.id).count() == 1

        decision = Decision.query.filter_by(user_id=self.test_user.id)[0]
        expected_object = {'decision': DECLINED_STATE_NAME, 'datetime': tstamp}
        for k, v in expected_object.items():
            assert getattr(decision, k) == v

        expected_presentation = decision.to_dict()
        assert json.loads(rv.data) == {'requirements': EXAMPLE_REQUIREMENTS, 'decision': expected_presentation}

    @mock.patch('wk_client.logic.evaluate_decision')
    @mock.patch('wk_client.logic.check_requirements')
    @mock.patch('wk_client.logic.get_requirements')
    def test_get_decision_fails(self, mock_get_requirements, mock_check_requirements, mock_evaluate_decision):
        @staticmethod
        def raise_value_error():
            raise ValueError

        mock_check_requirements.return_value = True
        mock_get_requirements.return_value = EXAMPLE_REQUIREMENTS

        mock_evaluate_decision.side_effect = raise_value_error
        mock_evaluate_decision.return_value = DecisionParams(
            approved=True,
            params={'amount': 5000, 'interest_rate': 0.0005, 'fee_amount': 0, 'fee_rate': 0}
        )
        tstamp = datetime(2018, 5, 4, 14, 3, 12)
        rv = post_json(self.client, '/get_decision', data={}, username=b'user2', password=b'pass2', timestamp=tstamp)
        assert rv.status == '200 OK'
        assert Decision.query.filter_by(user_id=self.test_user.id).count() == 1

        decision = Decision.query.filter_by(user_id=self.test_user.id)[0]
        expected_object = {
            'decision': DECLINED_STATE_NAME,
            'datetime': tstamp,
            'interest_daily': None,
            'amount': None,
            'duration_days': None,
            'repayment_frequency_days': None,
            'fee_rate': None,
            'fee_amount': None
        }

        for k, v in expected_object.items():
            assert getattr(decision, k) == v

        expected_presentation = decision.to_dict()
        assert json.loads(rv.data)['decision'] == expected_presentation


class TestGetDecision(AppTestCase):
    def test_full_approve(self):
        test_user = create_user('user3', 'pass3', 'acc3')
        data = {
            'basic_questions': {
                'first_name': 'Trusty',
                'last_name': 'McTrustFace',
                'date_of_birth': '1974-12-21',
            },
            'credit_report': {'score': 1},
            'company_report': {'opinion': 'passable'},
        }
        tstamp = datetime(2018, 7, 3, 4, 3, 1)

        rv = post_json(self.client, '/get_decision', data=data, username=b'user3', password=b'pass3', timestamp=tstamp)

        assert rv.status == '200 OK'

        assert Decision.query.filter_by(user_id=test_user.id).count() == 1
        decision = Decision.query.filter_by(user_id=test_user.id)[0]
        expected_object = {
            'decision': APPROVED_STATE_NAME,
            'datetime': tstamp,
            'interest_daily': 0.0005,
            'amount': 5000.,
            'duration_days': 360,
            'repayment_frequency_days': 30,
            'fee_rate': 0,
            'fee_amount': 0
        }

        for k, v in expected_object.items():
            assert getattr(decision, k) == v, k

        expected_response = {
            'requirements': EXAMPLE_REQUIREMENTS,
            'decision': {
                'status': 'Approved',
                'reference': str(decision.id),
                'product': PRODUCT_NAME,
                'amount_min': MIN_LOAN_AMOUNT,
                'amount_max': 5000.,
                'duration': 360,
                'interest_type': 'Compound',
                'interest': 0.20016,
                'fee_flat': 0,
                'fee_rate': 0,
                'repayment_type': 'Equal Repayment',
                'repayment_frequency': '30d',
                'valid_until': datetime(2018, 7, 10).date().isoformat(),
            }
        }
        assert json.loads(rv.data) == expected_response

    def test_full_decline(self):
        test_user = create_user('user4', 'pass4', 'acc4')
        data = {
            'basic_questions': {
                'first_name': 'Shady',
                'last_name': 'McShadyFace',
                'date_of_birth': '1994-12-21',
            },
            'credit_report': {'score': 1},
            'company_report': {'opinion': 'passable'},
        }

        tstamp = datetime(2018, 7, 3, 4, 3, 1)

        rv = post_json(self.client, '/get_decision', data=data, username=b'user4', password=b'pass4', timestamp=tstamp)

        assert rv.status == '200 OK'

        assert Decision.query.filter_by(user_id=test_user.id).count() == 1
        decision = Decision.query.filter_by(user_id=test_user.id)[0]
        expected_object = {
            'decision': DECLINED_STATE_NAME,
            'datetime': tstamp,
            'interest_daily': None,
            'amount': None,
            'duration_days': None,
            'repayment_frequency_days': None,
            'fee_rate': None,
            'fee_amount': None
        }

        for k, v in expected_object.items():
            assert getattr(decision, k) == v, k


class TestRequestFunding(AppTestCase):
    def setUp(self):
        super(TestRequestFunding, self).setUp()
        self.test_user = create_user('user4', 'pass4', 'acc4')
        self.timestamp = datetime(2018, 4, 5, 15, 5, 5)

    def post_with_auth(self, data):
        return post_json(
            self.client, '/request_funding', data=data, username=b'user4', password=b'pass4', timestamp=self.timestamp)

    def assert_invalid_decision(self, response, error_message=b'Invalid Decision'):
        assert '400' in response.status
        assert error_message in response.data
        assert Loan.query.filter_by(user_id=self.test_user.id).count() == 0
        assert CashFlow.query.filter_by(user_id=self.test_user.id).count() == 0

    def test_without_decision(self):
        payload = {'amount': 4000, 'approval_reference': 1}
        response = self.post_with_auth(payload)
        self.assert_invalid_decision(response)

    def test_with_decline(self):
        DeclineFactory(user=self.test_user, datetime=self.timestamp - timedelta(minutes=5))
        payload = {'amount': 4000, 'approval_reference': 1}
        response = self.post_with_auth(payload)
        self.assert_invalid_decision(response)

    def test_latest_decline(self):
        DeclineFactory(user=self.test_user, datetime=self.timestamp - timedelta(minutes=5))
        ApprovalFactory(user=self.test_user, datetime=self.timestamp - timedelta(minutes=10), id=3)
        payload = {'amount': 4000, 'approval_reference': 3}
        response = self.post_with_auth(payload)
        self.assert_invalid_decision(response)

    def test_timedout_approval(self):
        ApprovalFactory(user=self.test_user, datetime=self.timestamp - timedelta(days=10), id=4)
        payload = {'amount': 4000, 'approval_reference': 4}
        response = self.post_with_auth(payload)
        self.assert_invalid_decision(response)

    def test_more_than_approved_for(self):
        ApprovalFactory(user=self.test_user, datetime=self.timestamp - timedelta(minutes=10), amount=3000, id=5)
        payload = {'amount': 4000, 'approval_reference': 5}
        response = self.post_with_auth(payload)
        self.assert_invalid_decision(response, b'Invalid Amount')

    def test_wrong_approval(self):
        ApprovalFactory(user=self.test_user, datetime=self.timestamp - timedelta(minutes=10), amount=5000, id=6)
        ApprovalFactory(user=self.test_user, datetime=self.timestamp - timedelta(minutes=5), amount=5000, id=7)
        payload = {'amount': 4000, 'approval_reference': 6}
        response = self.post_with_auth(payload)
        self.assert_invalid_decision(response)

    def test_less_than_min(self):
        ApprovalFactory(user=self.test_user, datetime=self.timestamp - timedelta(minutes=5), amount=5000, id=8)
        payload = {'amount': MIN_LOAN_AMOUNT - 1, 'approval_reference': 8}
        response = self.post_with_auth(payload)
        self.assert_invalid_decision(response, b'Invalid Amount')

    @mock.patch('wk_client.bank.send_cash')
    def test_request_funding(self, mock_send_cash):
        mock_send_cash.return_value = {
            'amount': 3500, 'timestamp': self.timestamp + timedelta(minutes=1), 'bank_ref': 'foo'}
        ApprovalFactory(user=self.test_user, datetime=self.timestamp - timedelta(minutes=5), amount=5000, id=9)
        payload = {'amount': 3500, 'approval_reference': 9}
        response = self.post_with_auth(payload)
        assert response.status == '200 OK'

        response_body = json.loads(response.data)
        assert set(response_body.keys()) == set(['funding_reference', 'repayment_schedule', 'repayment_account'])

        exp_schedule = {(self.timestamp.date() + timedelta(30 * i)).isoformat(): 321.1 for i in range(1, 12)}
        exp_schedule[(self.timestamp.date() + timedelta(30 * 12)).isoformat()] = 321.08
        assert response_body['repayment_schedule'] == exp_schedule
        assert response_body['repayment_account'] == BANK_ACCOUNT

        assert Loan.query.filter_by(user_id=self.test_user.id).count() == 1
        loan = Loan.query.filter_by(user_id=self.test_user.id)[0]

        expected_loan_params = {
            'id': response_body['funding_reference'],
            'start_datetime': self.timestamp + timedelta(minutes=1),
            'opening_balance': 3500,
            'duration_days': 360,
            'interest_daily': 0.0005,
            'repayment_frequency_days': 30,
            'repayment_amount': 321.1
        }
        for k, v in expected_loan_params.items():
            assert getattr(loan, k) == v

        mock_send_cash.assert_called_with(amount=3500, account_to='acc4')

        assert CashFlow.query.filter_by(user_id=self.test_user.id).count() == 1
        cashflow = CashFlow.query.filter_by(user_id=self.test_user.id)[0]
        expected_cashflow_params = {
            'datetime': self.timestamp + timedelta(minutes=1),
            'amount': -3500,
            'type': 0,
            'bank_ref': 'foo'
        }

        for k, v in expected_cashflow_params.items():
            assert getattr(cashflow, k) == v

    @mock.patch('wk_client.bank.send_cash')
    def test_succeed_with_outstanding_balance(self, mock_send_cash):
        mock_send_cash.return_value = {
            'amount': 2000,
            'timestamp': self.timestamp + timedelta(minutes=1),
            'bank_ref': 'foo'
        }
        ApprovalFactory(
            user=self.test_user,
            datetime=self.timestamp - timedelta(days=5, minutes=10),
            id=10,
            amount=5000
        )
        create_loan_with_funding(
            user=self.test_user,
            funding_amount=3000,
            start_datetime=self.timestamp - timedelta(minutes=10)
        )
        payload = {'amount': 2000, 'approval_reference': 10}
        response = self.post_with_auth(payload)

        assert response.status == '200 OK'
        response_body = json.loads(response.data)

        assert Loan.query.filter_by(user_id=self.test_user.id).count() == 2
        loan = Loan.query.get(response_body['funding_reference'])

        expected_loan_params = {
            'start_datetime': self.timestamp + timedelta(minutes=1),
            'opening_balance': 5000,
            'duration_days': 360,
            'interest_daily': 0.0005,
            'repayment_frequency_days': 30,
            'repayment_amount': 458.72
        }
        for k, v in expected_loan_params.items():
            assert getattr(loan, k) == v

        mock_send_cash.assert_called_with(amount=2000, account_to='acc4')

    @mock.patch('wk_client.bank.send_cash')
    def test_fail_with_outstanding_balance(self, mock_send_cash):
        mock_send_cash.return_value = {
            'amount': 2000, 'timestamp': self.timestamp + timedelta(minutes=1), 'bank_ref': 'foo'}
        ApprovalFactory(
            user=self.test_user, datetime=self.timestamp - timedelta(days=5, minutes=10), id=10, amount=5000)
        create_loan_with_funding(
            user=self.test_user, funding_amount=3000, start_datetime=self.timestamp - timedelta(minutes=10))
        payload = {'amount': 3000, 'approval_reference': 10}
        response = self.post_with_auth(payload)

        assert '400' in response.status
        assert b'Invalid Amount' in response.data
        assert Loan.query.filter_by(user_id=self.test_user.id).count() == 1
        assert CashFlow.query.filter_by(user_id=self.test_user.id).count() == 1

    @mock.patch('wk_client.bank.send_cash')
    def test_requires_authorization(self, mock_send_cash):
        mock_send_cash.return_value = {
            'amount': 3500, 'timestamp': self.timestamp + timedelta(minutes=1), 'bank_ref': 'foo'}
        ApprovalFactory(user=self.test_user, datetime=self.timestamp - timedelta(minutes=5), amount=5000, id=9)
        payload = {'amount': 3500, 'approval_reference': 9}
        response = post_json(self.client, '/request_funding', data=payload, timestamp=self.timestamp)
        assert '200' not in response.status
        assert not mock_send_cash.called

    @mock.patch('wk_client.bank.send_cash')
    def test_sending_cash_failed(self, mock_send_cash):
        def raise_value_error(*args, **kwargs):
            raise ValueError
        mock_send_cash.side_effect = raise_value_error
        mock_send_cash.return_value = {
            'amount': 3500, 'timestamp': self.timestamp + timedelta(minutes=1), 'bank_ref': 'foo'}
        ApprovalFactory(user=self.test_user, datetime=self.timestamp - timedelta(minutes=5), amount=5000, id=9)
        payload = {'amount': 3500, 'approval_reference': 9}
        response = self.post_with_auth(payload)
        assert response.status_code == 400

    @mock.patch('wk_client.bank.send_cash')
    def test_request_funding_with_fee(self, mock_send_cash):
        mock_send_cash.return_value = {
            'amount': 4000, 'timestamp': self.timestamp + timedelta(minutes=1), 'bank_ref': 'foo'}
        ApprovalFactory(user=self.test_user, datetime=self.timestamp - timedelta(minutes=5), amount=5000, id=9, fee_amount=100, fee_rate=0.001)
        payload = {'amount': 4000, 'approval_reference': 9}
        response = self.post_with_auth(payload)
        assert response.status == '200 OK'

        response_body = json.loads(response.data)
        assert set(response_body.keys()) == set(['funding_reference', 'repayment_schedule', 'repayment_account'])

        exp_schedule = {(self.timestamp.date() + timedelta(30 * i)).isoformat(): 376.52 for i in range(1, 12)}
        exp_schedule[(self.timestamp.date() + timedelta(30 * 12)).isoformat()] = 376.4
        assert response_body['repayment_schedule'] == exp_schedule
        assert response_body['repayment_account'] == BANK_ACCOUNT

        assert Loan.query.filter_by(user_id=self.test_user.id).count() == 1
        loan = Loan.query.filter_by(user_id=self.test_user.id)[0]

        expected_loan_params = {
            'id': response_body['funding_reference'],
            'start_datetime': self.timestamp + timedelta(minutes=1),
            'opening_balance': 4000 + 100 + 4,
            'duration_days': 360,
            'interest_daily': 0.0005,
            'repayment_frequency_days': 30,
            'repayment_amount': 376.52
        }
        for k, v in expected_loan_params.items():
            assert getattr(loan, k) == v

        mock_send_cash.assert_called_with(amount=4000, account_to='acc4')

        assert CashFlow.query.filter_by(user_id=self.test_user.id).count() == 2
        cashflows = CashFlow.query.filter_by(user_id=self.test_user.id)
        expected_funding_params = {
            'datetime': self.timestamp + timedelta(minutes=1),
            'amount': -4000,
            'type': 0,
            'bank_ref': 'foo'
        }

        expected_fee_params = {
            'datetime': self.timestamp + timedelta(minutes=1),
            'amount': -104,
            'type': 2,
        }

        for k, v in expected_funding_params.items():
            assert getattr(cashflows[0], k) == v

        for k, v in expected_fee_params.items():
            assert getattr(cashflows[1], k) == v
