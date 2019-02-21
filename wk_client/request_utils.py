from flask import request
import dateutil.parser

from werkzeug.exceptions import BadRequest


def time_now():
    try:
        return dateutil.parser.parse(request.headers['Timestamp'])
    except (KeyError, ValueError) as e:
        raise BadRequest("Misconfigured timestamp")
