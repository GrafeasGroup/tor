import re

__version__ = "0.6.0"

# CTRL+C handler variable
is_running = True

_missing = object()


# @see https://stackoverflow.com/a/17487613/1236035
class cached_property(object):
    """A decorator that converts a function into a lazy property.  The
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
    """

    # implementation detail: this property is implemented as non-data
    # descriptor. non-data descriptors are only invoked if there is no
    # entry with the same name in the instance's __dict__. this allows
    # us to completely get rid of the access function call overhead. If
    # one choses to invoke __get__ by hand the property will still work
    # as expected because the lookup logic is replicated in __get__ for
    # manual invocation.

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, _type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


MOD_SUPPORT_PHRASES = [
    re.compile("fuck", re.IGNORECASE),
    re.compile("undo", re.IGNORECASE),
    re.compile("help", re.IGNORECASE),
    # re.compile('(?:good|bad) bot', re.IGNORECASE),
]

CLAIM_PHRASES = ["claim", "dibs", "clai", "caim", "clam", "calim", "dib"]
DONE_PHRASES = ["done", "deno", "doen", "dome", "doone"]
UNCLAIM_PHRASES = ["unclaim", "cancel", "unclai"]
