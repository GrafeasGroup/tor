from typing import Dict

import requests
# from praw.models import Comment
# from tor.core.config import Config


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

        self.http = requests.Session()
        self.http.headers.update({'Authorization': f'Api-Key {api_key}'})

    def _login(self) -> requests.Response:
        resp = self.http.post(
            self.login_url, data={
                'email': self.email, 'password': self.password
            }
        )
        return resp

    def _call(self, method: str, path: str, data: Dict = None, json: Dict = None, params: Dict = None) -> requests.Response:
        if not path.endswith('/'):
            raise ValueError("Path argument must end in a slash!")

        # https://2.python-requests.org/en/master/user/advanced/#prepared-requests
        req = requests.Request(method=method, url=(self.base_url + path), json=json, data=data, params=params)

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

    def get(self, path: str, data=None, json=None, params=None) -> requests.Response:
        return self._call('GET', path, data, json, params)

    def post(self, path: str, data=None, json=None, params=None) -> requests.Response:
        data = data if data else {}
        # grab csrf token
        self._call('GET', path, data, json, params)
        if 'csrftoken' in self.http.cookies:
            data.update({'csrfmiddlewaretoken': self.http.cookies.get('csrftoken')})
        return self._call('POST', path, data, json, params)

    def patch(self, path: str, data=None, json=None, params=None) -> requests.Response:
        return self._call('PATCH', path, data, json, params)

    def ping(self) -> str:
        return self._call('GET', '/ping/').json().get('ping?!')


# def get_blossom_volunteer_from_post(comment: Comment, cfg: Config) -> Optional[Dict]:
#     resp = cfg.blossom.get(
#         '/volunteer/', params={'username', comment.author.name}
#     )
#     if resp.get('results'):
#         return resp['results'][0]
#     else:
#         return None
