from enum import Enum, auto
from typing import Any, Dict

from requests import Request, Response, Session


class CocResponse(Enum):
    ok = auto()
    already_accepted = auto()


class UnclaimResponse(Enum):
    ok = auto()
    claimed_by_another = auto()
    not_claimed = auto()
    already_completed = auto()


class ClaimResponse(Enum):
    ok = auto()
    needs_coc = auto()
    claimed_by_another = auto()
    already_completed = auto()


class DoneResponse(Enum):
    ok = auto()
    unclaimed = auto()
    claimed_by_another = auto()
    already_completed = auto()


class BlossomAPI(object):
    def __init__(self, email: str, password: str, api_key: str, api_base_url: str = "http://api.grafeas.localhost:8000", login_url: str = "http://grafeas.localhost:8000/login/"):
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

        self.http = Session()
        self.http.headers.update({'Authorization': f'Api-Key {api_key}'})

    def _login(self) -> Response:
        resp = self.http.post(
            self.login_url, data={
                'email': self.email, 'password': self.password
            }
        )
        return resp

    def _call(self, method: str, path: str, data: Dict = None, json: Dict = None, params: Dict = None) -> Response:
        if not path.endswith('/'):
            raise ValueError("Path argument must end in a slash!")

        # https://2.python-requests.org/en/master/user/advanced/#prepared-requests
        req = Request(method=method, url=(self.base_url + path), json=json, data=data, params=params)

        for _ in range(3):
            prepped = self.http.prepare_request(req)
            settings = self.http.merge_environment_settings(prepped.url, {}, None, None, None)
            resp = self.http.send(prepped, **settings)

            if resp.status_code == 403:
                if resp.json().get('detail') == 'Authentication credentials were not provided.':
                    self._login()
                else:
                    break
            else:
                break
        else:
            raise Exception("Unable to authenticate! Check your email and password!")
        return resp

    def get(self, path: str, data=None, json=None, params=None) -> Response:
        r = self._call('GET', path, data, json, params)
        return r

    def post(self, path: str, data=None, json=None, params=None) -> Response:
        data = data if data else {}
        # grab csrf token
        self._call('GET', path, data, json, params)
        if 'csrftoken' in self.http.cookies:
            data.update({'csrfmiddlewaretoken': self.http.cookies.get('csrftoken')})
        r = self._call('POST', path, data, json, params)
        return r

    def patch(self, path: str, data=None, json=None, params=None) -> Response:
        r = self._call('PATCH', path, data, json, params)
        return r

    def ping(self) -> str:
        return self._call('GET', '/ping/').json().get('ping?!')

    #######################
    # VOLUNTEERS TO TRACK #
    # ------------------- #
    def get_volunteer(self, username: str) -> Dict[str, Any]:
        resp = self.get('/volunteer/', params={'username': username})
        resp.raise_for_status()
        data = resp.json()
        return next(iter(data['results']), {})

    def create_volunteer(self, username: str) -> Dict[str, Any]:
        resp = self.post('/volunteer/', data={'username': username})
        resp.raise_for_status()
        return resp.json()

    def patch_volunteer(self, user_id: str, data: Dict[str, Any]) -> None:
        resp = self.patch(f'/volunteer/{user_id}/', data=data)
        resp.raise_for_status()

    def accept_coc(self, username: str) -> CocResponse:
        volunteer = self.get_volunteer(username)
        if volunteer.get('id') is None:
            volunteer = self.create_volunteer(username)
        if volunteer.get('accepted_coc', False):
            return CocResponse.already_accepted

        self.patch_volunteer(volunteer['id'], {'accepted_coc': True})
        return CocResponse.ok

    ##################
    # POSTS TO CLAIM #
    # -------------- #
    def get_post(self, reddit_id: str) -> Dict[str, Any]:
        resp = self.get('/submission/', params={'submission_id': reddit_id})
        resp.raise_for_status()
        data = resp.json()
        return next(iter(data['results']), {})

    def create_post(self, reddit_id: str, reddit_url: str, tor_url: str) -> Dict[str, Any]:
        resp = self.post('/submission/', data={
            'submission_id': reddit_id,
            'source': 'transcribersofreddit',
            'url': reddit_url,
            'tor_url': tor_url,
        })
        resp.raise_for_status()
        post_id = int(resp.json()['message'].strip('Post object ').strip(' created!'))
        return self.get(f'/submission/{post_id}/').json()

    def claim_post(self, post_id: str, volunteer_id: str) -> ClaimResponse:
        resp = self.post(f'/submission/{post_id}/claim/', data={'v_id': volunteer_id})
        if resp.status_code == 200:
            return ClaimResponse.ok
        elif resp.status_code == 409:
            return ClaimResponse.claimed_by_another

        resp.raise_for_status()
        # Not sure what happened, but the `.raise_for_status()`
        # part should have caught all other error conditions, so
        # we must be fine
        return ClaimResponse.ok

    def complete_post(self, post_id: str, username: str, override: bool = False) -> DoneResponse:
        resp = self.post(f'/submission/{post_id}/done/', data={'username': username, 'mod_override': override})
        if resp.status_code == 200:
            return DoneResponse.ok
        elif resp.status_code == 409:
            return DoneResponse.already_completed
        elif resp.status_code == 412:
            data = resp.json()
            if 'not yet been claimed' in data['message']:
                return DoneResponse.unclaimed
            return DoneResponse.claimed_by_another

        resp.raise_for_status()
        # Not sure what happened, but the `.raise_for_status()`
        # part should have caught all other error conditions, so
        # we must be fine
        return DoneResponse.ok
