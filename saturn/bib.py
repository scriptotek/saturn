# coding=utf-8

from lxml import etree
from weakref import ReferenceType
import logging
from .marc import Record

log = logging.getLogger(__name__)

class Bib(object):
    """ An Alma Bib record """

    def __init__(self, alma: ReferenceType, xml: str):
        self.orig_xml = xml
        self.alma = alma  # weakref!
        self.init(xml)

    def init(self, xml: str):
        self.doc = etree.fromstring(xml.encode('utf-8'))
        self.id = self.doc.findtext('mms_id')
        self.marc_record = Record(self.doc.find('record'))
        self.cz_id = self.doc.findtext('linked_record_id[@type="CZ"]') or None
        self.nz_id = self.doc.findtext('linked_record_id[@type="NZ"]') or None

    def xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n%s' %
            etree.tounicode(self.doc)
        )

    def dump(self, filename: str):
        # Dump record to file
        with open(filename, 'wb') as file:
            file.write(etree.tostring(self.doc, pretty_print=True))

    def get_representations(self) -> dict:
        response = self.alma().get('/bibs/%s/representations' % self.id, headers={'Accept': 'application/json'})
        return response.json()['representation']

    def get_best_representation_id(self) -> str:
        # Use the FIRST representation. A bit simplistic for now.
        # Note: Representations live in IZ
        representations = self.get_representations()
        if len(representations) == 0:
            raise RuntimeError('No digital representations found!')
        if len(representations) > 1:
            log.warning('There are %d digital representations, will select the first one', len(representations))
        return representations[0]['id']


