# coding=utf-8

import os
import shutil
import sys
import argparse
import yaml
from requests.exceptions import HTTPError
import logging
import logging.config
import pkg_resources

from . import __version__
from .alma import Alma
from .data import Table
from .config import config
from .urn_service import UrnService

LOG_CONFIG_FILE = pkg_resources.resource_filename('saturn', 'logging.yml')

with open(LOG_CONFIG_FILE) as fp:
    logging.config.dictConfig(yaml.load(fp))

log = logging.getLogger()


class Saturn(object):

    def __init__(self, cfg: dict):
        self.default_data_file = cfg['default_data_file']
        self.table = Table()
        self.urn = UrnService(**cfg['urn'])
        self.alma = {
            'iz': Alma(**cfg['alma_iz']),
            'nz': Alma(**cfg['alma_nz']),
        }

    def run(self):
        parser = argparse.ArgumentParser(
            prog='saturn',
            description="""Simple Alma Tool for URN management using a CSV file. To register a new record,
            run 'saturn add {mms_id}, where {mms_id} is the institution zone MMS ID. To validate all records,
            run 'saturn validate'. See README.md for more details.
            """
        )
        parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
        parser.add_argument('-f', '--filename', dest='filename', nargs='?',
                            help='Data file to use. Default: {}'.format(self.default_data_file),
                            default=self.default_data_file)
        parser.add_argument('action', nargs=1, help='Action ("init", "add" or "verify")')
        parser.add_argument('records', nargs='*', help='Records to add or verify')

        args = parser.parse_args(sys.argv[1:])

        self.table.open(args.filename)

        action = args.action[0]

        if action == 'init':
            src_file = pkg_resources.resource_filename('saturn', '.env.dist')
            if os.path.exists('.env'):
                print('.env file already exists')
                sys.exit(1)
            shutil.copy(src_file, '.env')
            print('An .env file has been created in the current directory. Now modify it to will.')
            return

        if action == 'add':
            if len(args.records) > 0:
                try:
                    self.add_record(args.records[0])
                    self.update_record(args.records[0])
                except HTTPError as err:
                    print(err.response.text)
                    if err.response.status_code == 400:
                        log.error('Record does not exists according to the Alma API')
                    else:
                        log.error('Alma API returned error %s %s', err.response.status_code, err.response.text)
                    sys.exit(1)
            return

        if action == 'validate':
            self.validate_records()
            return

        print('Unknown action "%s", try saturn -h' % args.action)

    def add_record(self, mms_id):
        """
        Add a new record to our database and create an URN for it none exist yet.

        Params:
            mms_id: Institutional zone MMS ID
        """
        self.alma['iz'].get_record(mms_id) # Just validate that it exists
        self.table.add(mms_id)
        log.info('Added %s to data table', mms_id)

    def update_record(self, mms_id):
        """
        Validate an existing record in our database and create an URN for it none exist yet.

        Params:
            mms_id: Institutional zone MMS ID
        """
        row = self.table.get(mms_id)
        bib = self.alma['iz'].get_record(mms_id)

        if row['alma_nz_id'] == '':
            row['alma_nz_id'] = bib.nz_id or ''

        if row['alma_representation_id'] == '':
            row['alma_representation_id'] = bib.get_best_representation_id()

        if row['url'] == '':
            row['url'] = self.alma['iz'].get_delivery_url(bib)

        if row['title'] == '':
            row['title'] = bib.marc_record.get_title_statement()

        if row['alma_nz_id'] != '':
            # If record exists in NZ, we need to update that record
            bib = self.alma['nz'].get_record(row['alma_nz_id'])

        if row['urn'] == '':
            row['urn'] = self.get_urn(bib, row['url'])
            self.table.save()  # Save after each URN so we don't loose an URN if the MARC update fails

        self.check_urn(row['urn'], row['url'] )

        # Add URN to either the network zone record or the institution zone record, if no NZ record is present.
        self.add_urn_to_marc_record(bib, row['urn'])

        self.table.save()  # Save after each add to be safe

    def check_urn(self, urn, url):
        res = self.urn.find(urn)
        if res['defaultURL'] == url:
            log.info('%s has the expected target URL', urn)
        else:
            log.warning('Target URL for %s is %s, different from the expected %s', res['defaultURL'] , url)

    def validate_records(self):
        """
        Validate all records and makes updates as needed
        """
        for row in self.table.rows:
            self.update_record(row['alma_iz_id'])
        log.info('Validated %d records', len(self.table.rows))

    def get_urn(self, bib, url):
        """
        Return existing URN or create a new one.

        Params:
            bib: Record to check
            url: New URL to register if bib record does not have URN yet
        """
        urn = bib.marc_record.get_urn()
        if urn is not None:
            log.info('Record already had URN: %s', urn)
            return urn

        log.info('Creating URN pointing to %s', url)
        return self.urn.create(url)

    def add_urn_to_marc_record(self, bib, new_urn):
        """
        Add URN to Alma MARC record in 024 $2 urn
        """
        urn = bib.marc_record.get_urn()
        if urn is not None:
            if urn != new_urn:
                log.error('URN mismatch for record %s: %s != %s', bib.id, urn, new_urn)
            return

        field = bib.marc_record.add_datafield('024', '7', '0')
        field.add_subfield('a', new_urn)
        field.add_subfield('2', 'urn')

        bib.alma().put_record(bib, show_diff=True)
        log.info('Added URN %s to MARC record %s', new_urn, bib.id)


def main():
    Saturn(config()).run()
