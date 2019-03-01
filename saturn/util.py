# coding=utf-8
from __future__ import unicode_literals
import difflib
from colorama import Fore
from lxml import etree


def color_diff(diff):
    for line in diff:
        if line.startswith('+'):
            yield Fore.GREEN + line + Fore.RESET
        elif line.startswith('-'):
            yield Fore.RED + line + Fore.RESET
        elif line.startswith('^'):
            yield Fore.BLUE + line + Fore.RESET
        else:
            yield line


def line_marc(root: etree._Element) -> list:
    st = []
    for node in root.xpath('//datafield'):
        t = '%s %s%s' % (node.get('tag'), node.get('ind1').replace(' ', '#'), node.get('ind2').replace(' ', '#'))
        for sf in node.findall('subfield'):
            t += ' $%s %s' % (sf.get('code'), sf.text)
        t += '\n'
        st.append(t)

    return st


def get_diff(src: str, dst: str) -> list:
    src_lines = line_marc(etree.fromstring(src.encode('utf-8')))
    dst_lines = line_marc(etree.fromstring(dst.encode('utf-8')))

    return list(color_diff(
        difflib.unified_diff(src_lines, dst_lines, fromfile='Original', tofile='Modified')
    ))

