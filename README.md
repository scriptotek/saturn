# SATURN (Simple Alma Tool for URNs)

Saturn is a simple tool to manage (create, update and validate) URNs for records
in Alma Digital.

All URNs created using Saturn are stored in `saturn-data.csv`.
Each row contains
* The URN
* The Alma institution zone MMS ID
* The Alma network zone MMS ID (if a network zone record exists)
* The Alma representation ID
* The delivery URL
* The document title (just in case the Alma MMS IDs stop working and we need to look
  up things manually)

## Setup

The tool is not yet on PyPI. Clone the repository or download a zipped version
and unzip it. Inside the project directory, run `pip install .` to install the
command line tool.

Once installed, you can run the command line tool from the same directory or
from another one which we can call the 'working directory'. The latter can be
useful if you want to keep your URN data in a separate Git repository.

In the working directory, run `saturn init`. This will create an `.env` file
with all the configuration settings. Edit the file in your favourite text editor
to add credentials for the URN service and an API key for Alma. If your Alma
instance is connected to a network zone, a network zone API key must also be
included.
    
    URN_SERVICE=https://www.nb.no/idtjeneste/ws?wsdl
    URN_SERIES=URN:NBN:no
    URN_USERNAME=
    URN_PASSWORD=
    
    ALMA_API_KEY=
    ALMA_API_KEY_NZ=
    ALMA_DELIVERY_URL_TEMPLATE=https://bibsys.alma.exlibrisgroup.com/view/delivery/47BIBSYS_UBO/{mms_id}

## Usage

### Adding a record

To add a record, run `saturn add {MMS_ID}`, where MMS_ID is the instition zone MMS ID.
Saturn will then

1. Fetch the Alma Bib record from institution zone (using the institution zone API key)
2. Verify that it has digital representations.
3. Register a new URN with the URN service, using the
   `ALMA_DELIVERY_URL_TEMPLATE` template to format the target url.
4. Store the newly created URN in our local CSV file, then add it to the Alma Bib
   record (network zone record if present, institution zone otherwise) in a 024
   field having `$2 urn`.
   Question: Is this acceptable use of the 024 according to the cataloguing standard?
   A possible alternative would be to use 856 instead.

Note: If the bibliographic record already contains an URN, saturn will not create
a new one.

### Validating records

Run `saturn validate` to validate all records in the local CSV file.

### Adding a record that already has an URN

Run `saturn add --urn {URN} {MMS_ID}`, where `{MMS_ID}` is the instition zone MMS ID
and `{URN}` is the existing URN.

If the existing URN points to another URL, use `saturn add --urn {URN} --update_urns {MMS_ID}`
to update the URN target.
