# coding=utf-8
import logging
import weakref
from io import BytesIO
from requests import Session, HTTPError
from textwrap import dedent
import questionary  # type: ignore

from .util import get_diff
from .bib import Bib

log = logging.getLogger(__name__)


class LibrarySystem(object):

    def get_record(self, record_id: str):
        raise NotImplementedError()

    def put_record(self, record: Bib):
        raise NotImplementedError()


class Alma(LibrarySystem):

    name = None

    def __init__(self, api_region: str, api_key: str, delivery_url_template: str = None, dry_run: bool = False):
        self.dry_run = dry_run
        self.api_region = api_region
        self.api_key = api_key
        self.session = Session()
        self.session.headers.update({'Authorization': 'apikey %s' % api_key})
        self.base_url = 'https://api-{region}.hosted.exlibrisgroup.com/almaws/v1'.format(region=self.api_region)
        self.delivery_url_template = delivery_url_template

    def url(self, path: str, **kwargs) -> str:
        return self.base_url.rstrip('/') + '/' + path.lstrip('/').format(**kwargs)

    def get(self, url: str, **kwargs):
        return self.session.get(self.url(url), **kwargs)

    def get_record(self, record_id: str) -> Bib:
        """
        Get a Bib record from Alma

        :type record_id: string
        """
        response = self.get('/bibs/%s' % record_id)
        response.raise_for_status()
        record = Bib(weakref.ref(self), response.text)
        if record.id != record_id:
            raise RuntimeError('Response does not contain the requested MMS ID. %s != %s'
                               % (record.id, record_id))
        return record

    def put_record(self, record: Bib, show_diff: bool = False):
        """
        Store a Bib record to Alma

        Args:
            record: The Bib object
            show_diff: Whether to print a diff before saving
        """
        if record.cz_id is not None:
            log.warning(dedent(
                '''\
                Encountered a Community Zone record. Updating such records through the API will
                currently cause them to be de-linked from CZ, which is probably not what you want.
                Until Ex Libris fixes this, you're best off editing the record manually in Alma.\
                '''))

            if not questionary.confirm('Do you want to update the record and break CZ linkage?', default=False).ask():
                log.warning(' -> Skipping this record. You should update it manually in Alma!')
                return

            log.warning(' -> Updating the record. The CZ connection will be lost!')

        post_data = record.xml()
        if show_diff:
            the_diff = ''.join(get_diff(record.orig_xml, post_data))
            log.info('Diff:\n%s', the_diff)

        if not self.dry_run:
            try:
                response = self.session.put(self.url('/bibs/{mms_id}', mms_id=record.id),
                                            data=BytesIO(post_data.encode('utf-8')),
                                            headers={'Content-Type': 'application/xml'})
                response.raise_for_status()
                record.init(response.text)

            except HTTPError:
                msg = '*** Failed to save record %s --- Please try to edit the record manually in Alma ***'
                log.error(msg, record.id)

    def get_delivery_url(self, bib: Bib) -> str:
        # Get delivery url
        if self.delivery_url_template is None:
            raise RuntimeError('No delivery URL template set for this Alma instance.')
        return self.delivery_url_template.format(mms_id=bib.id, representation_id=bib.get_best_representation_id())

