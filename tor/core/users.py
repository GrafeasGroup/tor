"""
This is a standalone addition which contains a non-thread-safe implementation
of a dict user object that is stored in Redis. It can either take in an active
Redis connection as an argument or create its own with some defaults.
"""
import json
import logging
from typing import Any, Dict

from redis import StrictRedis

UserData = Dict[str, Any]


class UserDataNotFound(Exception):
    pass


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
        self, username: str, redis_conn: StrictRedis, create_if_not_found=True
    ):
        """
        Create our own Redis connection if one is not passed in.
        We also assume that there is already a logging object created.

        :param username: String; the username we're looking for. No fuzzing
            here; this must be exact.
        :param redis: Object; a `StrictRedis` instance.
        """
        if not redis_conn:
            raise ValueError("Missing Redis connection")
        if not username:
            raise ValueError("Username not supplied")

        super().__init__()
        self.redis = redis_conn
        self.username = username

        self.create_if_not_found = create_if_not_found
        self.redis_key = "::user::{}"
        self.user_data = self._load()

    def __repr__(self) -> str:
        return repr(self.user_data)

    def get(self, key: str, default_return=None) -> Any:
        return self.user_data.get(key, default_return)

    def _load(self) -> UserData:
        """
        :return: Dict or None; the loaded information from Redis.
        """
        result = self.redis.get(self.redis_key.format(self.username))
        if not result:
            if self.create_if_not_found:
                logging.debug("Did not find existing user, loaded blank slate.")
                return self._create_default_user_data()
            else:
                logging.debug("User not found, returning None.")
                raise UserDataNotFound()

        return json.loads(result.decode())

    def save(self) -> None:
        self.redis.set(self.redis_key.format(self.username), json.dumps(self.user_data))

    def update(self, key: str, value: Any) -> None:
        self.user_data[key] = value

    def list_update(self, key: str, value: Any) -> None:
        if not self.user_data.get(key):
            self.user_data[key] = []
        self.user_data[key] += [value]

    def _create_default_user_data(self) -> UserData:
        self.user_data = {}
        self.user_data.update({"username": self.username})
        return self.user_data
