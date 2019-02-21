from hashlib import sha256

from werkzeug.exceptions import BadRequest

from wk_client import auth, db
from wk_client.models import User
from flask import g


def hash_pw(password, username):
    # Don't use sha256 if you actually care about security. But here we need speed.
    return sha256(password.encode('utf-8') + username.encode('utf-8')).hexdigest()


def create_user(username, password, account):
    hashed_pw = hash_pw(password, username)
    if User.query.filter_by(username=username).scalar():
        raise BadRequest()
    user = User(username=username, hashed_password=hashed_pw, account=account)
    db.session.add(user)
    db.session.commit()
    return user


@auth.verify_password
def verify_password(username, password):
    # TODO: Don't verify if the request is coming from untrusted authority.
    user = User.query.filter_by(username=username).first_or_404()
    if hash_pw(password, username) == user.hashed_password:
        g.user = user
        return True
    return False
