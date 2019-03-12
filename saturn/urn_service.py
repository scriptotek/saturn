from zeep import Client as SoapClient  # type: ignore
import logging

log = logging.getLogger(__name__)


class UrnService(object):

    def __init__(self, url: str, series: str, username: str, password: str) -> None:
        self.series = series
        self.client = SoapClient(url)
        self.service = self.client.service
        self.session_token = None
        self.username = username
        self.password = password

    def create(self, url: str) -> str:
        if self.session_token is None:
            self.session_token = self.service.login(self.username, self.password)

        info = self.service.createURN(self.session_token, self.series, url)
        log.info('Created new URN: %s', info['URN'])
        return str(info['URN'])

    def update(self, urn: str, old_url: str, new_url: str) -> None:
        if self.session_token is None:
            self.session_token = self.service.login(self.username, self.password)

        info = self.service.replaceURL(self.session_token, urn, old_url, new_url)
        if info['URN'] != urn:
            print(info)
            raise RuntimeError('Unexpected response')
        log.info('Updated URL target for URN: %s', info['URN'])

    def get_url(self, urn: str) -> str:
        res = self.service.findURN(urn)
        return str(res['defaultURL'])
