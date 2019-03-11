# coding=utf-8
from __future__ import unicode_literals

import logging
from lxml import etree

log = logging.getLogger(__name__)


class Subfield(object):
    """ A Marc21 subfield """
    def __init__(self, node):
        self.node = node

    @property
    def code(self):
        return self.node.get('code')

    @property
    def text(self):
        return self.node.text

    @text.setter
    def text(self, value):
        self.node.text = value

    def __str__(self):
        return self.text


class Field(object):
    """ A Marc21 field """

    def __init__(self, node):
        self.node = node

    @property
    def tag(self):
        return self.node.get('tag')

    @property
    def ind1(self):
        return self.node.get('ind1')

    @property
    def ind2(self):
        return self.node.get('ind2')

    def __str__(self):
        items = [self.tag, self.ind1.replace(' ', '#') + self.ind2.replace(' ', '#')]
        for subfield in self.node:
            items.append('$%s %s' % (subfield.attrib['code'], subfield.text))
        return ' '.join(items)

    @property
    def subfields(self):
        return self.get_subfields()

    def get_subfields(self, source_code=None):
        for node in self.node.findall('subfield'):
            if source_code is None or source_code == node.get('code'):
                yield Subfield(node)

    def sf(self, code=None):
        # return text of first matching subfield or None
        for node in self.get_subfields(code):
            return node.text

    def set_tag(self, value):
        if self.node.get('tag') != value:
            log.debug('CHANGE: Set tag to %s in `%s`', value, self)
            self.node.set('tag', value)
            return 1
        return 0

    def set_ind1(self, value):
        if value is not None and value != '?' and self.node.get('ind1') != value:
            log.debug('CHANGE: Set ind1 to %s in `%s`', value, self)
            self.node.set('ind1', value)
            return 1
        return 0

    def set_ind2(self, value):
        if value is not None and value != '?' and self.node.get('ind2') != value:
            log.debug('CHANGE: Set ind2 to %s in `%s`', value, self)
            self.node.set('ind2', value)
            return 1
        return 0

    def add_subfield(self, code, value):
        subel = etree.SubElement(self.node, 'subfield', {'code': code})
        subel.text = value


class Record(object):
    """ A Marc21 record """

    def __init__(self, el: etree._Element):
        self.el = el

    @property
    def id(self) -> str:
        return self.el.findtext('./controlfield[@tag="001"]')

    @property
    def fields(self):
        return self.get_fields()

    def get_fields(self):
        for node in self.el.findall('datafield'):
            yield Field(node)

    def remove_field(self, field):
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

    def get_urn(self) -> str:
        for field in self.fields:
            if field.tag == '024' and field.sf('2') == 'urn':
                return field.sf('a')
