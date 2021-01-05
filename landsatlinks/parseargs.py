import argparse
from datetime import date


def parse_cli_arguments():

    currentDate = date.today().strftime('%Y-%m-%d')

    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--results',
                        required=True,
                        help='Path to the file containing the search result.This will be created during the first '
                             'search. This file should be in the download directory to allow creating new download '
                             'links when the old ones expired. The text file containing the download links will be '
                             'stored in the same directory.')
    parser.add_argument('-s', '--satellite',
                        required=True,
                        choices=['TM', 'ETM', 'OLI'],
                        help='The satellite that scenes are requested for.')
    parser.add_argument('-p', '--pathrowlist',
                        required=True,
                        help='Text file containing allowed pathrows, one per line. Format: PPPRRR '
                             '(Keep padding zeroes!).')
    parser.add_argument('-d', '--daterange', default=f'1970-01-01,{currentDate}',
                        help='Start date and end date = date range to be considered. Format: YYYY-MM-DD,YYYY-MM-DD.'
                             'Default: full archive until today.')
    parser.add_argument('-c', '--cloudcover',
                        default='0,100',
                        help='Percent (land) cloud cover range to be considered.\nDefault: 0,100')
    parser.add_argument('-m', '--months',
                        default='1,2,3,4,5,6,7,8,9,10,11,12',
                        help='Seasonal filter: define the months to be considered.\nDefault: 1,2,3,4,5,6,7,8,9,10')
    parser.add_argument('-t', '--tier',
                        default='T1',
                        help='Landsat collection tier level. Valid tiers: T1,T2,RT\nDefault: T1')

    args = parser.parse_args()

    return args
