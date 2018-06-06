"""
This is a standalone addition which contains a non-thread-safe implementation
of a dict user object that is stored in Redis. It can either take in an active
Redis connection as an argument or create its own with some defaults.
"""
import os
import json
import logging

import redis


class UserError(Exception):
    def __init__(self, message, *args):
        self.message = message  # bypass DeprecationWarning
        super().__init__(message, *args)


class UserConnectionError(Exception):
    def __init__(self, message, *args):
        self.message = message  # bypass DeprecationWarning
        super().__init__(message, *args)


class User(object):
    """
    Usage:
    from users import User

    pam = User('pam', redis_conn=config.redis)
    pam.update('age', 39)
    pam.update('position', 'Office Administrator')
    pam.save()
    """
    def __init__(
            self, username=None, redis_conn=None, create_if_not_found=True
    ):
        """
        Create our own Redis connection if one is not passed in.
        We also assume that there is already a logging object created.

        :param username: String; the username we're looking for. No fuzzing
            here; this must be exact.
        :param redis: Object; a `redis` instance.
        """

        super().__init__()
        if redis_conn:
            self.r = redis_conn
        else:
            try:
                url = os.getenv(
                    'REDIS_CONNECTION_URL', 'redis://localhost:6379/0'
                )
                self.r = redis.StrictRedis.from_url(url)
                self.r.ping()
            except redis.exceptions.ConnectionError:
                raise UserConnectionError('Unable to reach Redis.')

        if not username:
            raise UserError('Username not supplied.')
        self.username = username

        self.create_if_not_found = create_if_not_found
        self.redis_key = '::user::{}'
        self.user_data = self._load()

    def __repr__(self):
        return repr(self.user_data)

    def get(self, key, default_return=None):
        return self.user_data.get(key, default_return)

    def _load(self):
        """
        :return: Dict or None; the loaded information from Redis.
        """
        result = self.r.get(self.redis_key.format(self.username))
        if not result:
            if self.create_if_not_found:
                logging.debug(
                    'Did not find existing user, loaded blank slate.'
                )
                return self._create_default_user_data()
            else:
                logging.debug('User not found, returning None.')
                return None

        return json.loads(result.decode())

    def save(self):
        self.r.set(
            self.redis_key.format(self.username),
            json.dumps(self.user_data)
        )

    def update(self, key, value):
        self.user_data[key] = value

    def _create_default_user_data(self):
        self.user_data = dict()
        self.user_data.update({'username': self.username})
        return self.user_data


if __name__ == '__main__':
    pam = User('pam')
    print(pam)
    pam.update('transcriptions', pam.get('transcriptions', 1) + 1)
    print(pam.get('transcriptions'))
    pam.save()