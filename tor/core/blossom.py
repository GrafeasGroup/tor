import requests


class ConfigurationError(Exception):
    pass


class BlossomAPI(object):
    def __init__(
            self,
            email: str=None,
            password: str=None,
            api_key: str=None,
            api_base_url: str="http://api.grafeas.localhost:8000",
            login_url: str="http://grafeas.localhost:8000/login/"
    ):
        if not email:
            raise ConfigurationError("Need an email address!")
        if not password:
            raise ConfigurationError("Need a password!")
        if not api_key:
            raise ConfigurationError("Need an API key!")

        self.email = email
        self.password = password
        self.base_url = api_base_url
        self.login_url = login_url

        self.s = requests.Session()
        self.s.headers.update({'Authorization': f'Api-Key {api_key}'})

    def _login(self):
        resp = self.s.post(
            self.login_url, data={
                'email': self.email, 'password': self.password
            }
        )
        return resp

    def _call(self, method: str, path: str, data=None, json=None, params=None):
        # https://2.python-requests.org/en/master/user/advanced/#prepared-requests
        req = requests.Request(
            method=method,
            url=self.base_url+path,
            json=json,
            data=data,
            params=params
        )

        for _ in range(3):
            prepped = self.s.prepare_request(req)
            settings = self.s.merge_environment_settings(prepped.url, {}, None, None, None)
            resp = self.s.send(prepped, **settings)

            if resp.status_code == 403:
                if resp.json().get('detail') == "Authentication credentials were not provided.":
                    self._login()
            else:
                break
        else:
            raise Exception("Unable to authenticate! Check your email and password!")
        return resp

    def get(self, path, data=None, json=None, params=None):
        return self._call('GET', path, data, json, params)

    def post(self, path, data=None, json=None, params=None):
        data = data if data else {}
        # grab csrf token
        resp = self._call('GET', path, data, json, params)
        if 'csrftoken' in self.s.cookies:
            data.update({'csrfmiddlewaretoken': self.s.cookies.get('csrftoken')})
        return self._call('POST', path, data, json, params)

    def patch(self, path, data=None, json=None, params=None):
        return self._call('PATCH', path, data, json, params)
