# coding=utf-8
from __future__ import unicode_literals
from typing import Optional, Iterator, Iterable
import logging
from lxml import etree  # type: ignore

log = logging.getLogger(__name__)


class Subfield(object):
    """ A Marc21 subfield """
    def __init__(self, node: etree._Element) -> None:
        self.node = node

    @property
    def code(self) -> Optional[str]:
        return self.node.get('code') or None

    @property
    def text(self) -> str:
        return self.node.text or ''

    @text.setter
    def text(self, value: str) -> None:
        self.node.text = value

    def __str__(self) -> str:
        return self.text


class Field(object):
    """ A Marc21 field """

    def __init__(self, node: etree._Element) -> None:
        self.node = node

    @property
    def tag(self) -> str:
        return self.node.get('tag') or ''

    @property
    def ind1(self) -> str:
        return self.node.get('ind1') or ' '

    @property
    def ind2(self) -> str:
        return self.node.get('ind2') or ' '

    def __str__(self) -> str:
        items = [self.tag, self.ind1.replace(' ', '#') + self.ind2.replace(' ', '#')]
        for subfield in self.node:
            items.append('$%s %s' % (subfield.attrib['code'], subfield.text))
        return ' '.join(items)

    @property
    def subfields(self) -> Iterator[Subfield]:
        return self.get_subfields()

    def get_subfields(self, source_code:Optional[str]=None) -> Iterator[Subfield]:
        for node in self.node.findall('subfield'):
            if source_code is None or source_code == node.get('code'):
                yield Subfield(node)

    def sf(self, code:Optional[str]=None) -> Optional[str]:
        # return text of first matching subfield or None
        for node in self.get_subfields(code):
            return node.text
        return None

    def set_tag(self, value: str) -> None:
        if self.node.get('tag') != value:
            log.debug('CHANGE: Set tag to %s in `%s`', value, self)
            self.node.set('tag', value)

    def set_ind1(self, value: str) -> None:
        if value is not None and value != '?' and self.node.get('ind1') != value:
            log.debug('CHANGE: Set ind1 to %s in `%s`', value, self)
            self.node.set('ind1', value)

    def set_ind2(self, value: str) -> None:
        if value is not None and value != '?' and self.node.get('ind2') != value:
            log.debug('CHANGE: Set ind2 to %s in `%s`', value, self)
            self.node.set('ind2', value)

    def add_subfield(self, code: str, value: str) -> None:
        subel = etree.SubElement(self.node, 'subfield', {'code': code})
        subel.text = value


class Record(object):
    """ A Marc21 record """

    def __init__(self, el: etree._Element):
        self.el = el

    @property
    def id(self) -> Optional[str]:
        return self.el.findtext('./controlfield[@tag="001"]') or None

    @property
    def fields(self) -> Iterator[Field]:
        return self.get_fields()

    def get_fields(self) -> Iterator[Field]:
        for node in self.el.findall('datafield'):
            yield Field(node)

    def remove_field(self, field: Field) -> None:
        # field: Field
        self.el.remove(field.node)

    def add_datafield(self, tag: str, ind1: str, ind2: str) -> Field:
        new_field = Field(etree.Element('datafield', {
            'tag': tag,
            'ind1': ind1,
            'ind2': ind2,
        }))
        numeric_tag = int(tag)

        idx = 0
        for field in self.fields:
            try:
                node_tag = int(field.tag)
            except ValueError:  # Alma includes non-numeric tags like 'AVA'
                continue

            if node_tag > numeric_tag:
                break
            idx = self.el.index(field.node)

        self.el.insert(idx + 1, new_field.node)
        return new_field

    def get_title_statement(self) -> str:
        field = self.el.find('./datafield[@tag="245"]')
        return ' '.join([sf.text.strip() for sf in field.findall('./subfield')])

    def get_urn(self) -> Optional[str]:
        for field in self.fields:
            if field.tag == '024' and field.sf('2') == 'urn':
                return field.sf('a')
        return None
