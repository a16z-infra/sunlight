import requests


class DiffbotClient(object):

    BASE_API_URL = 'http://api.diffbot.com'
    TIMEOUT_MS = 15000

    def request(self, url, token, api, version=3):
        ''' Issue a request to the Diffbot API and return the response if valid JSON '''
        params = {'url': url, 'token': token, 'timeout': self.TIMEOUT_MS}

        try:
            response = requests.get(f'{self.BASE_API_URL}/v{version}/{api}', params=params, timeout=self.TIMEOUT_MS)
            response.raise_for_status()
        except:
            raise Exception('REMOTE_ERROR')

        return response.json()
