import os
from typing import Dict, Union, Optional
from dotenv import load_dotenv  # type: ignore
load_dotenv('.env')


def config() -> Dict[str, Union[str, Dict[str, Optional[str]]]]:
    return {
        'default_data_file': 'saturn-data.csv',
        'urn': {
            'url': os.getenv('URN_SERVICE', 'https://www.nb.no/idtjeneste/ws?wsdl'),
            'series': os.getenv('URN_SERIES', 'URN:NBN:no'),
            'username': os.getenv('URN_USERNAME'),
            'password': os.getenv('URN_PASSWORD'),
        },
        'alma_iz': {
            'api_region': 'eu',
            'api_key': os.getenv('ALMA_API_KEY'),
            'delivery_url_template': os.getenv('ALMA_DELIVERY_URL_TEMPLATE', 'https://bibsys.alma.exlibrisgroup.com/view/delivery/47BIBSYS_UBO/{mms_id}'),
        },
        'alma_nz': {
            'api_region': 'eu',
            'api_key': os.getenv('ALMA_API_KEY_NZ'),
        }
    }

