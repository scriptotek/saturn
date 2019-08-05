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
from typing import TYPE_CHECKING

from . import __version__
from .alma import Alma
from .data import Table
from .config import config
from .urn_service import UrnService

if TYPE_CHECKING:
    from .bib import Bib

LOG_CONFIG_FILE = pkg_resources.resource_filename('saturn', 'logging.yml')

with open(LOG_CONFIG_FILE) as fp:
    logging.config.dictConfig(yaml.safe_load(fp))

log = logging.getLogger()


class Saturn(object):

    def __init__(self, cfg: dict) -> None:
        self.default_data_file = cfg['default_data_file']
        self.table = Table()
        self.urn = UrnService(**cfg['urn'])
        self.alma = {
            'iz': Alma(**cfg['alma_iz']),
            'nz': Alma(**cfg['alma_nz']),
        }

    def run(self) -> None:
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

        subparsers = parser.add_subparsers(dest='action',
                                           description='add, init or validate')

        add_cmd = subparsers.add_parser('add')
        add_cmd.add_argument('--urn', dest='urn',
                             help='Update an existing URN to point to the added record.')
        add_cmd.add_argument('--update_urns', action='store_true', dest='update_urns',
                            help='Update URNs to match template.')
        add_cmd.add_argument('--update_marc_record', action='store_true', dest='update_marc_record',
                            help='Update MARC record')  # Skal? Skal ikke???
        add_cmd.add_argument('records', nargs='*', help='Records to add or validate')

        init_cmd = subparsers.add_parser('init')
        validate_cmd = subparsers.add_parser('validate')
        validate_cmd.add_argument('--update_urns', action='store_true', dest='update_urns',
                                  help='Update URNs to match template.')
        validate_cmd.add_argument('--update_marc_record', action='store_true', dest='update_marc_record',
                                  help='Update MARC record')  # Skal? Skal ikke???

        args = parser.parse_args(sys.argv[1:])

        self.table.open(args.filename)

        action = args.action

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
                    defaults = {}
                    if args.urn:
                        defaults['urn'] = args.urn
                    self.add_record(args.records[0], defaults)
                    self.update_record(
                        args.records[0],
                        update_urns=args.update_urns,
                        update_marc_record=args.update_marc_record
                    )
                except HTTPError as err:
                    print(err.response.text)
                    if err.response.status_code == 400:
                        log.error('Record does not exists according to the Alma API')
                    else:
                        log.error('Alma API returned error %s %s', err.response.status_code, err.response.text)
                    sys.exit(1)
            return

        if action == 'validate':
            self.validate_records(args.update_urns, args.update_marc_record)
            return

        print('Unknown action "%s", try saturn -h' % args.action)

    def add_record(self, mms_id: str, defaults: dict) -> None:
        """
        Add a new record to our database and create an URN for it none exist yet.

        Params:
            mms_id: Institutional zone MMS ID
        """
        if self.table.has(mms_id):
            print('Record already exists in the local database.')
            return
        self.alma['iz'].get_record(mms_id)  # Validate that the record exists in Alma
        row = self.table.add(mms_id)
        for key, val in defaults.items():
            row[key] = val

        log.info('Added %s to data table', mms_id)

    def update_row_from_bib(self, row, bib) -> None:
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
            log.info('Found record for mms id %s', row['alma_nz_id'])

    def update_record(self, mms_id: str, update_urns: bool, update_marc_record: bool) -> None:
        """
        Validate an existing record in our database and create an URN for it none exist yet.

        Params:
            mms_id: Institutional zone MMS ID
        """
        row = self.table.get(mms_id)
        bib = self.alma['iz'].get_record(mms_id)
        self.update_row_from_bib(row, bib)

        if row['urn'] == '':
            row['urn'] = self.get_or_create_urn(bib, row['url'])
            self.table.save()  # Save after each URN so we don't loose an URN if the MARC update fails

        self.check_urn_target(row['urn'], row['url'], update_urns)

        # Add URN to either the network zone record or the institution zone record, if no NZ record is present.
        if update_marc_record:
            self.add_urn_to_marc_record(bib, row['urn'])

        self.table.save()  # Save after each add to be safe

    def check_urn_target(self, urn: str, url: str, update: bool) -> None:
        """
        Validate and optionally fix the target URL for a given URN.

        Params:
            - urn: The URN to check
            - url: The expected target URL for the given URN
            - update: Whether to update the URN if the target URL differs from the expected value
        """
        current_url = self.urn.get_url(urn)
        if current_url == url:
            log.info('%s has the expected target URL', urn)
        elif update:
            self.urn.update(urn, current_url, url)
            log.info('%s: Target URL updated from %s to %s', urn, current_url, url)
        else:
            log.warning('%s: Target URL %s differs from the expected %s. Use --update_urns to update.', urn, current_url, url)

    def validate_records(self, update_urns: bool, update_marc_record: bool) -> None:
        """
        Validate all records and makes updates as needed
        """
        for row in self.table.rows:
            self.update_record(row['alma_iz_id'], update_urns, update_marc_record)
        log.info('Validated %d records', len(self.table.rows))

    def get_or_create_urn(self, bib: 'Bib', url: str) -> str:
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

    def add_urn_to_marc_record(self, bib: 'Bib', new_urn: str) -> None:
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

        bib.alma.put_record(bib, show_diff=True)
        log.info('Added URN %s to MARC record %s', new_urn, bib.id)


def main() -> None:
    Saturn(config()).run()
