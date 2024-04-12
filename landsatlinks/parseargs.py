import argparse
from datetime import date

from landsatlinks import __version__
from landsatlinks.utils import PROG_NAME


def parse_cli_arguments():

    currentDate = date.today().strftime('%Y%m%d')

    parser = argparse.ArgumentParser(
        description='Create download URLs for Landsat Collection 2 Level 1 product bundles using the USGS machine-to-machine API. '
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
    search_group = parser_search.add_mutually_exclusive_group()
    parser_search.add_argument(
        'aoi',
        help='Path to AOI file. '
             'Supported formats: .txt (one path/row per line in the format PPPRRR) or '
             '.shp, .geojson, .gpkg (vector files).'
    )
    parser_search.add_argument(
        'output_dir',
        help='Path to the output directory where the download links and downloaded products will be stored.'
    )
    # optional arguments
    parser_search.add_argument(
        '-s', '--sensor',
        default='TM,ETM,OLI',
        help='The sensor that scenes are requested for. Choose TM for Landsat 4/5, ETM for Landsat 7, '
             'or OLI for Landsat 8, or a comma-separated list (e.g. TM,ETM,OLI).'
    )
    parser_search.add_argument(
        '-d', '--daterange',
        default=f'19700101,{currentDate}',
        help='Start date and end date. Format: YYYYMMDD,YYYYMMDD.\n'
             'Default: beginning of archive until today.'
    )
    parser_search.add_argument(
        '-c', '--cloudcover',
        default='-1,100',
        help='Percent (land) cloud cover range to be considered. \nDefault: -1,100'
    )
    parser_search.add_argument(
        '-m', '--months',
        default='1,2,3,4,5,6,7,8,9,10,11,12',
        help='Seasonal filter - months to be considered. \nDefault: 1,2,3,4,5,6,7,8,9,10,11,12'
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

    search_group.add_argument(
        '--download',
        action='store_true',
        help='Download the product bundles directly after creating the download links.'
    )
    search_group.add_argument(
        '-n', '--no-action',
        action='store_true',
        help='Only search for product bundles and print info without generating links or downloading.'
    )
    parser_search.add_argument(
        '-f', '--forcelogs',
        help='Path to FORCE Level-2 log files. Will skip products that have been processed by FORCE.'
    )
    parser_search.add_argument(
        '-q', '--queue-file',
        help='Path to FORCE queue file. Downloaded product bundles will be appended to the queue.',
        default=None
    )
    parser_search.add_argument(
        '--secret',
        help='Path to the file containing the username and password for M2MApi access (EarthExplorer login). '
             'First line: username, second line: password.'
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
        help='Path to the output directory where the downloaded products will be stored.'
    )

    parser_dl.add_argument(
        '-q', '--queue-file',
        help='Path to FORCE queue file. Downloaded product bundles will be appended to the queue.',
        default=None
    )

    return parser.parse_args()
