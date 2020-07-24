from dataclasses import dataclass
from enum import auto, Enum
from typing import Any, Dict, Union

from requests import Request, Response, Session
from praw.models import Comment


class BlossomStatus(Enum):
    already_completed = auto()
    coc_not_accepted = auto()
    data_missing = auto()
    missing_prerequisite = auto()
    not_found = auto()
    ok = auto()
    other_user = auto()


@dataclass
class BlossomResponse:
    data: Union[Dict[str, Any], None] = None
    status: BlossomStatus = BlossomStatus.ok


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

    def delete(self, path: str, data=None, params=None) -> Response:
        """Request a DELETE request to the API."""
        return self._call("DELETE", path, data, params)

    def create_user(self, username: str) -> BlossomResponse:
        """Create a new user with the given username."""
        response = self.get("/volunteer/", data={"username": username})
        if response.status_code == 201:
            return BlossomResponse(status=BlossomStatus.ok, data=response.json())
        elif response.status_code == 422:
            return BlossomResponse(status=BlossomStatus.already_completed)
        response.raise_for_status()
        return BlossomResponse()

    def get_user(self, username: str) -> BlossomResponse:
        """Get the user with the specified username."""
        response = self.get("/volunteer", params={"username": username})
        response.raise_for_status()
        results = response.json()["results"]
        if results:
            return BlossomResponse(data=results[0])
        else:
            return BlossomResponse(status=BlossomStatus.not_found)

    def accept_coc(self, user_id: str) -> BlossomResponse:
        """Let the user accept the Code of Conduct."""
        response = self.get(f"/volunteer/{user_id}/accept_coc")
        if response.status_code == 201:
            return BlossomResponse()
        elif response.status_code == 404:
            return BlossomResponse(status=BlossomStatus.not_found)

        response.raise_for_status()
        return BlossomResponse()

    def create_submission(
            self, post_id: str, post_url: str, original_url: str
    ) -> BlossomResponse:
        """Create a Blossom Submission with the given information."""
        params = {
            "original_id": post_id,
            "origin": "reddit",
            "tor_url": post_url,
            "url": original_url
        }

        response = self.post("/submission", params=params)
        response.raise_for_status()
        return BlossomResponse(data=response.json())

    def get_submission(self, reddit_id: str) -> BlossomResponse:
        """Get the Blossom Submission corresponding to the provided Reddit ID."""
        response = self.get("/submission/", params={"original_id": reddit_id})
        response.raise_for_status()
        results = response.json()["results"]
        if results:
            return BlossomResponse(data=results[0])
        else:
            return BlossomResponse(status=BlossomStatus.not_found)

    def delete_submission(self, submission_id: str) -> BlossomResponse:
        """Delete a Submission from Blossom corresponding to the provided ID."""
        response = self.delete(f"/submission/{submission_id}")
        if response.status_code == 204:
            return BlossomResponse()

        response.raise_for_status()
        return BlossomResponse()

    def create_transcription(
        self, transcription: Comment, submission_id: str, removed_from_reddit: bool
    ) -> BlossomResponse:
        """Create a new Transcription within Blossom."""
        response = self.post(
            "/transcription/",
            data={
                "original_id": transcription.id,
                "submission_id": submission_id,
                "source": "reddit",
                "text": transcription.body,
                "url": transcription.permalink,
                "username": transcription.author.name,
                "removed_from_reddit": removed_from_reddit
            }
        )
        if response.status_code == 201:
            return BlossomResponse(data=response.json())
        elif response.status_code == 403:
            return BlossomResponse(status=BlossomStatus.coc_not_accepted)
        elif response.status_code == 404:
            return BlossomResponse(status=BlossomStatus.not_found)
        response.raise_for_status()
        return BlossomResponse()

    def claim_submission(self, submission_id: str, username: str) -> BlossomResponse:
        """Claim the specified submission with the specified username."""
        response = self.patch(
            f"/submission/{submission_id}/claim/", data={"username": username}
        )
        if response.status_code == 201:
            return BlossomResponse(data=response.json())
        elif response.status_code == 403:
            return BlossomResponse(status=BlossomStatus.coc_not_accepted)
        elif response.status_code == 404:
            return BlossomResponse(status=BlossomStatus.not_found)
        elif response.status_code == 409:
            return BlossomResponse(status=BlossomStatus.already_completed)
        response.raise_for_status()
        return BlossomResponse()

    def unclaim(self, submission_id: str, username: str) -> BlossomResponse:
        response = self.patch(
            f"/submission/{submission_id}/unclaim", data={"username": username}
        )
        if response.status_code == 201:
            return BlossomResponse(data=response.json())
        elif response.status_code == 404:
            return BlossomResponse(status=BlossomStatus.not_found)
        elif response.status_code == 406:
            return BlossomResponse(status=BlossomStatus.other_user)
        elif response.status_code == 409:
            return BlossomResponse(status=BlossomStatus.already_completed)
        elif response.status_code == 412:
            return BlossomResponse(status=BlossomStatus.missing_prerequisite)

        response.raise_for_status()
        return BlossomResponse()

    def done(
        self, submission_id: str, username: str, mod_override: bool = False
    ) -> BlossomResponse:
        """Specify that the submission is done by the provided username."""
        response = self.patch(
            f"/submission/{submission_id}/done",
            data={"username": username, "mod_override": mod_override}
        )
        if response.status_code == 201:
            return BlossomResponse(data=response.json())
        elif response.status_code == 403:
            return BlossomResponse(status=BlossomStatus.coc_not_accepted)
        elif response.status_code == 404:
            return BlossomResponse(status=BlossomStatus.not_found)
        elif response.status_code == 409:
            return BlossomResponse(status=BlossomStatus.already_completed)
        elif response.status_code == 412:
            return BlossomResponse(status=BlossomStatus.missing_prerequisite)
        elif response.status_code == 428:
            return BlossomResponse(status=BlossomStatus.data_missing)
        response.raise_for_status()
        return BlossomResponse()
