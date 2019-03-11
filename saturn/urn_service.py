from zeep import Client as SoapClient
import logging

log = logging.getLogger(__name__)


class UrnService(object):

    def __init__(self, url: str, series: str, username: str, password: str):
        self.series = series
        self.client = SoapClient(url)
        self.service = self.client.service
        self.session_token = None
        self.username = username
        self.password = password

    def create(self, url: str):
        if self.session_token is None:
            self.session_token = self.service.login(self.username, self.password)

        info = self.service.createURN(self.session_token, self.series, url)
        log.info('Created new URN: %s', info['URN'])
        return info['URN']

    def update(self, urn: str, old_url: str, new_url: str):
        if self.session_token is None:
            self.session_token = self.service.login(self.username, self.password)

        info = self.service.replaceURL(self.session_token, urn, old_url, new_url)
        if info['URN'] != urn:
            print(info)
            raise RuntimeError('Unexpected response')
        log.info('Updated URL target for URN: %s', info['URN'])

    def find(self, urn: str):
        return self.service.findURN(urn)
