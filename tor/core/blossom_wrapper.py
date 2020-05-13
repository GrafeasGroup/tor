from enum import Enum, auto
from typing import Dict

from requests import Request, Response, Session


class BlossomResponse(Enum):
    ok = auto()
    not_found = auto()
    missing_prerequisite = auto()
    other_user = auto()
    already_completed = auto()


class BlossomAPI:
    def __init__(
        self,
        email: str,
        password: str,
        api_key: str,
        api_base_url: str = "http://api.grafeas.localhost:8000",
        login_url: str = "http://grafeas.localhost:8000/login/",
        num_retries: int = 1,
    ) -> None:
        """
        Initialize the Blossom API with the necessary parameters.

        :param email: the email address which the bot should use to log into Blossom
        :param password: the password to use to log into Blossom
        :param api_key: the API key to use to perform requests to Blossom
        :param api_base_url: the base URL of the API used as a prefix to API paths
        :param login_url: the URL used to log the bot into Blossom
        :param num_retries: the number of retries each failing call should do before error
        """
        if not email:
            raise ValueError("Need an email address!")
        if not password:
            raise ValueError("Need a password!")
        if not api_key:
            raise ValueError("Need an API key!")
        if not api_base_url:
            raise ValueError("Need to know the API base URL!")
        if not login_url:
            raise ValueError("Need to know the login URL!")

        self.email = email
        self.password = password
        self.base_url = api_base_url
        self.login_url = login_url
        self.num_retries = num_retries

        self.http = Session()
        self.http.headers.update({"Authorization": f"Api-Key {api_key}"})

    def _login(self) -> Response:
        """Log into Blossom using the provided URL and credentials."""
        resp = self.http.post(
            self.login_url, data={"email": self.email, "password": self.password}
        )
        return resp

    def _call(
        self, method: str, path: str, data: Dict = None, params: Dict = None
    ) -> Response:
        """
        Create a call to the API using the requests package.

        In this method, a request is retried if a 403 and a message on authentication
        credentials is returned. In this case, it seems that tor is not yet logged in and
        hence we attempt to log in. In any other case, the request is returned at is
        without retrying. If the described failure still occurs after the set number of
        retries, this method raises an exception.

        Note that because of Blossom's CSRF protection each non-GET request also first
        requires a GET request to retrieve a CSRF token.
        """
        # https://2.python-requests.org/en/master/user/advanced/#prepared-requests
        data = data if data is not None else dict()
        params = params if params is not None else dict()

        if method != "GET":
            # Currently Blossom has CSRF protection enabled, hence tor should include a
            # new CSRF token in this request, which is retrieved from the GET request.
            self._call("GET", path, data, params)
            if "csrftoken" in self.http.cookies:
                data.update({"csrfmiddlewaretoken": self.http.cookies.get("csrftoken")})
        req = Request(method=method, url=self.base_url + path, data=data, params=params)

        for _ in range(self.num_retries):
            prepped = self.http.prepare_request(req)
            settings = self.http.merge_environment_settings(
                prepped.url, {}, None, None, None
            )
            resp = self.http.send(prepped, **settings)

            if resp.status_code == 403:
                if (
                    resp.json().get("detail")
                    == "Authentication credentials were not provided."
                ):
                    # It seems that the bot is not yet logged in, so perform the login.
                    self._login()
                else:
                    break
            else:
                break
        else:
            raise Exception("Unable to authenticate! Check your email and password!")
        return resp

    def get(self, path: str, data=None, params=None) -> Response:
        """Request a GET request to the API."""
        return self._call("GET", path, data, params)

    def post(self, path: str, data=None, params=None) -> Response:
        """Request a POST request to the API."""
        return self._call("POST", path, data, params)

    def patch(self, path: str, data=None, params=None) -> Response:
        """Request a PATCH request to the API."""
        return self._call("PATCH", path, data, params)
