import requests
from fetchers.base import BaseFetcher

class RestFetcher(BaseFetcher):

    def execute(self):
        r = requests.get(self.params["url"])
        r.raise_for_status()
        return r.json()
