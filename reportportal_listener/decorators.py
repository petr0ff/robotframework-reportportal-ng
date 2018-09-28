import logging

import six
import time
from urllib3.exceptions import ConnectionError, HTTPError, NewConnectionError, ResponseError

from robot.libraries.BuiltIn import BuiltIn


def retry(exceptions_to_check=(ConnectionError,
                               HTTPError,
                               NewConnectionError,
                               ResponseError,
                               UnicodeEncodeError,), wait=2, retries=3):
    """Decorator that provides retrying wrapped function in case of exception_to_check exception."""

    def wrapped_retry(f):

        @six.wraps(f)
        def wrapped_f(*args, **kwargs):
            attempts = retries + 1
            for attempt in range(attempts):
                try:
                    return f(*args, **kwargs)
                except exceptions_to_check as e:
                    if attempt < retries:
                        BuiltIn().log_to_console("%s, Retrying in %d seconds" % (e, wait))
                        time.sleep(wait)
                    else:
                        BuiltIn().log_to_console('No more retries')
                        raise
        return wrapped_f

    return wrapped_retry
