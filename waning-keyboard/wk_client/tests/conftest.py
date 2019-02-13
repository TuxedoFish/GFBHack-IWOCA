import base64
import json
import unittest

from wk_client import create_app, db
from wk_client.config import TestConfig


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()


def open_with_auth(client, url, method, username, password):
    return client.open(
        url,
        method=method,
        headers={
            'Authorization': encode_username_password(username, password)
        },
    )


def post_json(client, url, data, username=None, password=None, timestamp=None):
    params = {'method': 'post', 'content_type': 'application/json', 'data':json.dumps(data)}
    headers = params.get('headers', {})
    if username and password:
        headers['Authorization'] = encode_username_password(username, password)
    if timestamp:
        headers['Timestamp'] = timestamp.isoformat()
    params['headers'] = headers
    return client.open(url, **params)


def encode_username_password(username, password):
    return b'Basic ' + base64.b64encode(username + b":" + password)
