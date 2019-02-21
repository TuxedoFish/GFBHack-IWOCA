from datetime import datetime
from unittest import mock

from wk_client import bank
from wk_client.tests.conftest import AppTestCase


class TestSendCash(AppTestCase):
    def setUp(self):
        super(TestSendCash, self).setUp()
        self.frozen_time = datetime(2018, 5, 4, 12)

    @mock.patch('generate_transactions.time_now')
    def test_send_transaction(self, time_now):
        time_now.return_value = self.frozen_time
        transaction = bank.send_cash(100, 'foo')
        self.assertDictEqual(transaction, {'amount': 100., 'timestamp': self.frozen_time, 'bank_ref': transaction['bank_ref']})
        self.assertTrue(isinstance(transaction['bank_ref'], str))
