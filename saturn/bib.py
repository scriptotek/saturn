# coding=utf-8

from lxml import etree  # type: ignore
from weakref import ref
import logging
from typing import List, Dict, Any, TYPE_CHECKING
from .marc import Record

if TYPE_CHECKING:
    from .alma import Alma

log = logging.getLogger(__name__)


class Bib(object):
    """ An Alma Bib record """

    def __init__(self, alma: 'ref[Alma]', xml: str):
        self.orig_xml = xml
        self._alma = alma
        self.init(xml)

    def init(self, xml: str) -> None:
        self.doc = etree.fromstring(xml.encode('utf-8'))
        self.id = self.doc.findtext('mms_id')
        self.marc_record = Record(self.doc.find('record'))
        self.cz_id = self.doc.findtext('linked_record_id[@type="CZ"]') or None
        self.nz_id = self.doc.findtext('linked_record_id[@type="NZ"]') or None

    @property
    def alma(self):
        if self._alma() is None:
            raise RuntimeError('Alma object is no longer available')
        return self._alma()

    def xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n%s' %
            etree.tounicode(self.doc)
        )

    def dump(self, filename: str) -> None:
        # Dump record to file
        with open(filename, 'wb') as file:
            file.write(etree.tostring(self.doc, pretty_print=True))

    def get_representations(self) -> List[Dict[str, Any]]:
        response = self.alma.get('/bibs/%s/representations' % self.id, headers={'Accept': 'application/json'})
        return list(response.json()['representation'])

    def get_best_representation_id(self) -> str:
        # Use the FIRST representation. A bit simplistic for now.
        # Note: Representations live in IZ
        representations = self.get_representations()
        if len(representations) == 0:
            raise RuntimeError('No digital representations found!')
        if len(representations) > 1:
            log.warning('There are %d digital representations, will select the first one', len(representations))
        return str(representations[0]['id'])


