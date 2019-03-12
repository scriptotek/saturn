import csv
import os
from typing import Optional, List, Dict
from collections import OrderedDict

# Using Dict instead of OrderedDict because the latter will fail with Pytho 3.6
# See: https://stackoverflow.com/a/43583996/489916
Rows = List[Dict[str, str]]


class RowNotFound(RuntimeError):
    pass


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

    def __init__(self) -> None:
        self._rows: Rows = []

    def open(self, filename: str) -> 'Table':
        self.filename = filename
        rows: Rows = []
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
    def rows(self) -> Rows:
        return self._rows

    def save(self, filename: Optional[str] = None) -> None:
        filename = filename or self.filename
        if filename is None:
            raise ValueError('No filename given')

        with open(filename, 'w') as fp:
            writer = csv.DictWriter(fp, fieldnames=self.fieldnames)
            writer.writeheader()
            writer.writerows(self.rows)

    def has(self, mms_id: str) -> bool:
        for row in self.rows:
            if row['alma_iz_id'] == mms_id:
                return True
        return False

    def get(self, mms_id: str) -> Dict[str, str]:
        for row in self.rows:
            if row['alma_iz_id'] == mms_id:
                return row
        raise RowNotFound()

    def add(self, mms_id: str) -> None:
        if self.has(mms_id):
            raise ValueError('MMS ID already exists in DB')

        row: OrderedDict[str, str] = OrderedDict([(x, '') for x in self.fieldnames])
        row['alma_iz_id'] = mms_id
        self.rows.append(row)
        self.save()
