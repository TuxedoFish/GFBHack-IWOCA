from wk_client.auth_utils import create_user, hash_pw
from wk_client.models import User
from wk_client.tests.conftest import AppTestCase


class TestAuth(AppTestCase):
    def test_create_user_returns(self):
        user = create_user('foo', 'bar', 'baz')
        self.assertEqual(user.username, 'foo')
        self.assertNotEqual(user.hashed_password, 'bar')
        self.assertEqual(user.account, 'baz')

    def test_create_user_saves(self):
        _ = create_user('foo', 'bar', 'baz')
        user = User.query.filter_by(username='foo').one()
        self.assertNotEqual(user.hashed_password, 'bar')
        self.assertEqual(user.account, 'baz')

    def test_hased_password_matches(self):
        _ = create_user('foo', 'bar', 'baz')
        user = User.query.filter_by(username='foo').one()
        self.assertEqual(user.hashed_password, hash_pw('bar', 'foo'))


