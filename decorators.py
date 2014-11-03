import logging
import time
from functools import wraps
from google.appengine.runtime import DeadlineExceededError


def polycamp(f):
    """ decorator to enable passing either a campaign key or
    a complete campaign to a function. both will arrive as a campaign
    Atm, this only works if the campaign or campaign
    key is the first argument.
    """
    # avoid circular import
    import models

    @wraps(f)
    def wrapper(*args, **kwargs):
        if isinstance(args[0], basestring):
            camp = models.NearWooCampaignDS.urlsafe_get(args[0])
            args = tuple([camp]) + args[1:]
        return f(*args, **kwargs)
    return wrapper


def polycampkey(f):
    """ decorator to enable passing either a campaign key or
    a complete campaign to a function. both will arrive as a
    campaign key.
    Atm, this only works if the campaign or campaign
    key is the first argument.
    """
    import models

    @wraps(f)
    def wrapper(*args, **kwargs):
        if isinstance(args[0], models.NearWooCampaignDS):
            camp_key = args[0].key.urlsafe()
            args = tuple([camp_key]) + args[1:]
        return f(*args, **kwargs)
    return wrapper


def logcall(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        logging.info('call to %s', f.func_name)
        return f(*args, **kwargs)
    return wrapper


def trycatch(f):
    def tryit(*args, **kwargs):
        try:
            return f(*args, **kwargs), None
        except Exception as e:
            return False, e.message
    return tryit


def tryagain(ExceptionToCheck, tries=4, delay=3, backoff=2):
    """Retry calling the decorated function using exponential backoff.

    From: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
            exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will
        double the delay each retry
    :type backoff: int
    """
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except DeadlineExceededError:
                    # make sure we don't retry through the deadline exceeded
                    logging.error("out of time")
                    raise
                except ExceptionToCheck as e:
                    msg = ('%s, retrying in %d seconds...' %
                           (str(e), mdelay))
                    logging.warning(msg)
                    logging.exception(e)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry  # true decorator
    return deco_retry

# sentinel for missing value
_missing = object()


class cached_property(object):
    """A decorator that converts a function into a lazy property. The
    function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value::

    class Foo(object):

    @cached_property
    def foo(self):
    # calculate something important here
    return 42

    The class has to have a `__dict__` in order for this property to
    work.


    Taken directly from Armin Ronancher's Werkzeug utils library. (see
    licenses/WERKZEUG for copyright/license details)
    """

    # implementation detail: this property is implemented as non-data
    # descriptor. non-data descriptors are only invoked if there is
    # no entry with the same name in the instance's __dict__.
    # this allows us to completely get rid of the access function call
    # overhead. If one choses to invoke __get__ by hand the property
    # will still work as expected because the lookup logic is replicated
    # in __get__ for manual invocation.

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


