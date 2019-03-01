import csv
import os
from typing import Optional


class Table(object):

    fieldnames = [
        'urn',
        'alma_iz_id',
        'alma_nz_id',
        'alma_representation_id',
        'url',
        'title',
    ]
    filename = None

    def __init__(self):
        self._rows: list = []

    def open(self, filename: str):
        self.filename = filename
        rows: list = []
        if not os.path.exists(filename):
            self._rows = rows
            return self

        with open(filename) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                rows.append(row)
        self._rows = rows
        return self

    @property
    def rows(self) -> list:
        return self._rows

    def save(self, filename: str = None):
        filename = filename or self.filename
        if filename is None:
            raise ValueError('No filename given')

        with open(filename, 'w') as fp:
            writer = csv.DictWriter(fp, fieldnames=self.fieldnames)
            writer.writeheader()
            writer.writerows(self.rows)

    def get(self, mms_id: str) -> Optional[dict]:
        for row in self.rows:
            if row['alma_iz_id'] == mms_id:
                return row
        return None

    def add(self, mms_id: str):
        if self.get(mms_id) is not None:
            raise ValueError('MMS ID already exists in DB')

        row: dict = {x: '' for x in self.fieldnames}
        row['alma_iz_id'] = mms_id
        self.rows.append(row)
        self.save()
