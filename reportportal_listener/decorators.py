import logging

import six
import time


def retry(exceptions_to_check=(Exception,), wait=2, retries=3):
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
                        logging.warning("%s, Retrying in %d seconds", e, wait)
                        time.sleep(wait)
                    else:
                        logging.error('No more retries')
                        raise
        return wrapped_f

    return wrapped_retry
