import argparse
from datetime import date
from landsatlinks import __version__


def parse_cli_arguments():

    currentDate = date.today().strftime('%Y-%m-%d')

    parser = argparse.ArgumentParser(
        description='Creating download URLs for Landsat Collection 2 Level 1 data using the USGS machine-to-machine API'
    )

    # positional arguments
    parser.add_argument(
        'results',
        help='Path to the file containing the search results. This file should be in the download directory to allow '
             'creating new download links when the old ones expired. The text file containing the download links will '
             'be stored in the same directory.'
    )
    parser.add_argument(
        'sensor',
        choices=['TM', 'ETM', 'OLI'],
        help='The sensor that scenes are requested for. Choose TM for Landsat 4/5, ETM for Landsat 7, '
             'or OLI for Landsat 8.'
    )
    parser.add_argument(
        'pathrowlist',
        help='Path to text file containing allowed path/rows, one per line. Format: PPPRRR (keep padding zeroes!).'
    )

    # optional arguments
    parser.add_argument(
        '-d', '--daterange',
        default=f'1970-01-01,{currentDate}',
        help='Start date and end date = date range to be considered. Format: YYYY-MM-DD,YYYY-MM-DD. '
             'Default: full archive until today.'
    )
    parser.add_argument(
        '-c', '--cloudcover',
        default='0,100',
        help='Percent (land) cloud cover range to be considered. \nDefault: 0,100')
    parser.add_argument(
        '-m', '--months',
        default='1,2,3,4,5,6,7,8,9,10,11,12',
        help='Seasonal filter: define the months to be considered. \nDefault: 1,2,3,4,5,6,7,8,9,10,11,12'
    )
    parser.add_argument(
        '-t', '--tier',
        choices=['T1', 'T2'],
        default='T1',
        help='Landsat collection tier level. Valid tiers: T1,T2,RT \nDefault: T1'
    )
    parser.add_argument(
        '-l', '--level',
        choices=['L1TP', 'L1GT', 'L1GS'],
        default='L1TP',
        help='Landsat level of processing. Valid levels: L1TP, L1GT, L1GS'
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'landsatlinks version {__version__} https://github.com/ernstste/landsatlinks'
    )
    parser.add_argument(
        '-r', '--resume',
        action='store_true',
        help='Resume from prior search: Search the folder containing the results file for products that have already'
             'been downloaded and only create download links for products that were not downloaded yet.'
    )
    parser.add_argument(
        '-s', '--secret',
        help='Path to a file containing the username and password for the USGS EarthExplorer.'
    )
    parser.add_argument(
        '-f', '--forcelogs',
        help='Path to FORCE Level-2 log files. Search this folder for log files and only consider products that '
             'have not been processed before.'
    )

    return parser.parse_args()
