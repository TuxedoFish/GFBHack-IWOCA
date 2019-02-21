from wk_client.db_utils import nuke_database
from wk_client.models import User, Decision, Loan, CashFlow
from wk_client.tests.conftest import AppTestCase
from wk_client.tests.factories import DecisionFactory, LoanFactory, RepaymentFactory




class TestNukeDatabase(AppTestCase):
    @staticmethod
    def _create_some_data():
        DecisionFactory()
        LoanFactory()
        RepaymentFactory()

    @staticmethod
    def is_database_empty():
        for table in [User, Decision, Loan, CashFlow]:
            if getattr(table, 'query').count() > 0:
                return False
        return True

    def test_nuke_database(self):
        self._create_some_data()
        self.assertFalse(self.is_database_empty())
        nuke_database()
        self.assertTrue(self.is_database_empty())
