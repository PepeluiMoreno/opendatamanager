# app/resolver/rest_resolver.py
from app.resolver.base import BaseResolver, RawData, ParsedData, DomainData
import requests

class RESTResolver(BaseResolver):
    def __init__(self, endpoint: str, headers: dict | None):
        self.endpoint = endpoint
        self.headers = headers or {}

    def fetch(self) -> RawData:
        r = requests.get(self.endpoint, headers=self.headers)
        r.raise_for_status()
        return r.json()

    def parse(self, raw: RawData) -> ParsedData:
        return raw  # ya es dict

    def normalize(self, parsed: ParsedData) -> DomainData:
        return parsed  # delegamos al proyecto