import argparse
from datetime import date
from landsatlinks import __version__


def parse_cli_arguments():

    currentDate = date.today().strftime('%Y-%m-%d')

    parser = argparse.ArgumentParser(
        description='Create download URLs for Landsat Collection 2 Level 1 data using the USGS machine-to-machine API.'
                    'Try "landsatlinks search" to search for (and download) Landsat C1 Level 1 product bundles or '
                    '"landsatlinks download" to only download product bundles from a prior search. '
                    'Type "landsatlinks <command> --help" for more information on a specific command. '
                    'https://github.com/ernstste/landsatlinks'
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'landsatlinks version {__version__} https://github.com/ernstste/landsatlinks'
    )

    subparsers = parser.add_subparsers()

    # Search parser arguments
    parser_search = subparsers.add_parser(
        'search',
        help='Search for products, generate download links and optionally download the results.'
    )
    parser_search.add_argument(
        'pathrowlist',
        help='Path to text file containing allowed path/rows, one per line. Format: PPPRRR (keep padding zeroes!).'
    )
    parser_search.add_argument(
        'output_dir',
        help='Path to the output directory where the download links and downloaded products will be stored.'
    )
    # optional arguments
    parser_search.add_argument(
        '-s', '--sensor',
        choices=['TM', 'ETM', 'OLI'],
        default='TM,ETM,OLI',
        help='The sensor that scenes are requested for. Choose TM for Landsat 4/5, ETM for Landsat 7, '
             'or OLI for Landsat 8, or a comma-separated list (e.g. TM,ETM,OLI).'
    )
    parser_search.add_argument(
        '-d', '--daterange',
        default=f'1970-01-01,{currentDate}',
        help='Start date and end date = date range to be considered. Format: YYYY-MM-DD,YYYY-MM-DD.\n'
             'Default: full archive until today.'
    )
    parser_search.add_argument(
        '-c', '--cloudcover',
        default='0,100',
        help='Percent (land) cloud cover range to be considered. \nDefault: 0,100'
    )
    parser_search.add_argument(
        '-m', '--months',
        default='1,2,3,4,5,6,7,8,9,10,11,12',
        help='Seasonal filter: define the months to be considered. \nDefault: 1,2,3,4,5,6,7,8,9,10,11,12'
    )
    parser_search.add_argument(
        '-t', '--tier',
        choices=['T1', 'T2'],
        default='T1',
        help='Landsat collection tier level. Valid tiers: T1, T2, RT \nDefault: T1'
    )
    parser_search.add_argument(
        '-l', '--level',
        choices=['L1TP', 'L1GT', 'L1GS'],
        default='L1TP',
        help='Landsat level of processing. Valid levels: L1TP, L1GT, L1GS'
    )

    parser_search.add_argument(
        '--download',
        action='store_true',
        help='Download the product bundles directly after creating the download links.'
    )
    parser_search.add_argument(
        '-n', '--no-action',
        action='store_true',
        help='Only search for product bundles matching search criteria and print the total data volume. No download '
             'links will be created and no products will not be downloaded.'
    )
    parser_search.add_argument(
        '-f', '--forcelogs',
        help='Path to FORCE Level-2 log files. Search this folder for log files and only consider products that '
             'have not been processed before.'
    )
    parser_search.add_argument(
        '--secret',
        help='Path to a file containing the username and password for the USGS EarthExplorer.'
    )

    # Download parser arguments
    parser_dl = subparsers.add_parser(
        'download',
        help='Load URLs from a text file and download without creating download links first.'
    )
    parser_dl.add_argument(
        'url_file',
        help='Path to the file containing the urls to download.'
    )
    parser_dl.add_argument(
        'output_dir',
        help='Path to the output directory where the download links and downloaded products will be stored.'
    )

    return parser.parse_args()
