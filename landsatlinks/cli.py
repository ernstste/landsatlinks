import os
import re
import signal
from datetime import datetime
from getpass import getpass

from landsatlinks import download, utils, aoi
from landsatlinks.eeapi import eeapi
from landsatlinks.parseargs import parse_cli_arguments


def handler(signum, frame):
    print('\nCTRL+C detected, exiting')
    exit()


signal.signal(signal.SIGINT, handler)


def main():
    # ==================================================================================================================
    # 1. Check input and set up variables
    args = parse_cli_arguments()

    if not vars(args):
        print('No arguments provided, run "landsatlinks --help" for more information')
        exit(1)

    if all([arg in args for arg in ['url_file', 'output_dir']]):
        utils.check_os()
        utils.check_dependencies(['aria2c'])
        download.download_standalone(args.url_file, args.output_dir)
        exit(0)

    # Check platform and dependencies in case the -n/--no-download flag is not set
    if args.download:
        utils.check_os()
        utils.check_dependencies(['aria2c'])

    # validate output directory
    output_dir = os.path.realpath(args.output_dir)
    utils.validate_file_paths(output_dir, 'downloads', file=False)

    # load pathrow list
    prList = aoi.Aoi(args.aoi).get_footprints

    # dataset name
    if not all([sensor in ['TM', 'ETM', 'OLI'] for sensor in args.sensor.split(',')]):
        print('Error: Invalid sensor name. Please use one of the following: TM/ETM/OLI.\n'
              'A comma-separated combination of sensor names is also possible (e.g. ETM,OLI)\n'
              'Exiting.')
        exit(1)
    sat_dict = {'TM': 'landsat_tm_c2_l1', 'ETM': 'landsat_etm_c2_l1', 'OLI': 'landsat_ot_c2_l1'}
    datasetNames = [sat_dict[sensor] for sensor in args.sensor.split(',')]

    # validate dates and set range
    dates = args.daterange.split(',')
    for date in dates:
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            print('Error: Dates not provided in format YYYY-MM-DD,YYYY-MM-DD or date is invalid.')
            exit(1)
    start, end = dates
    # validate and set cloud cover thresholds
    minCC, maxCC = args.cloudcover.split(',')
    if not all([0 <= cc <= 100 for cc in [float(minCC), float(maxCC)]]):
        print('Error: Cloud cover values must be between 0 and 100.')
        exit(1)
    # seasonal filter
    seasonalFilter = [int(month) for month in args.months.split(',')]
    if not all([1 <= month <= 12 for month in seasonalFilter]):
        print('Error: Months must be between 1 and 12.')
        exit(1)
    # processing level
    dataTypeL1 = args.level
    # tier
    tier = args.tier
    # make sure chosen combinations of tier and dataTypeL1 make sense
    if dataTypeL1 != 'L1TP' and tier == 'T1':
        print('Error: Tier 1 selected with processing level L1GT or L1GS (tier defaults to T1 if not specified).\n'
              'Choose Tier 2 (T2) or Real-Time (RT) for processing levels lower than L1TP.')
        exit(1)

    # path to FORCE Level-2 logs
    if args.forcelogs:
        log_path = args.forcelogs
        utils.validate_file_paths(log_path, 'FORCE log', file=False, write=False)

    # ==================================================================================================================
    # 2. Run
    # Login
    if args.secret:
        secret = utils.load_secret(os.path.realpath(args.secret))
        user, passwd = secret
    else:
        user = input('Enter your USGS EarthExplorer username: ')
        passwd = getpass('Enter your USGS EarthExplorer password: ')
    api = eeapi(user, passwd)

    print(
        f'\nSensor(s): {args.sensor.replace(",", ", ")}\n'
        f'Tile(s): {",".join(prList)}\n'
        f'Date range: {start} to {end}\n'
        f'Included months: {",".join([str(month) for month in seasonalFilter])}\n'
        f'Cloud cover: {minCC}% to {maxCC}%\n'
    )

    # Get product IDs of products that match the search criteria
    dlProductIds = []
    for datasetName in datasetNames:
        dlProductIds.extend(
            api.retrieve_search_results(
                datasetName=datasetName, data_type_l1=dataTypeL1, tier=tier,
                start=start, end=end, seasonalFilter=seasonalFilter,
                minCC=minCC, maxCC=maxCC,
                prList=prList
            )
        )
    if not dlProductIds:
        print('No scenes matching search results found. Exiting.')
        exit(0)

    total_size = utils.bytes_to_humanreadable(sum([s.get('filesize') for s in dlProductIds]))
    print(
        f'{len(dlProductIds)} Landsat Level 1 scenes matching criteria found\n'
        f'{total_size} data volume found'
    )

    # Check for FORCE Level-2 log files in the filesystem
    if args.forcelogs:
        print('\nChecking file system for FORCE Level-2 processing log files.')
        productIdsLogs = utils.find_files(search_path=log_path, search_type='log', recursive=True)
        if len(productIdsLogs) == 0:
            print(f'No FORCE logs found at {log_path}')
        else:
            dlProductIds = [productid for productid in dlProductIds if productid['displayId'] not in productIdsLogs]
            print(
                f'{len(productIdsLogs)} FORCE log files found, '
                f'{len(dlProductIds)} products from search results not processed by FORCE yet.\n'
                f'Remaining download size: {utils.bytes_to_humanreadable(sum([s.get("filesize") for s in dlProductIds]))}'
            )

    if args.no_action:
        exit(0)

    # Generate download links and save to disk
    urls = api.get_download_links(dl_product_ids=dlProductIds)
    timeNow = datetime.now().strftime('%Y%m%dT%H%M%S')
    links_path = os.path.join(
        output_dir,
        f'urls_landsat_{args.sensor.replace(",", "_")}_{timeNow}.txt'
    )
    print(f'Writing download links to {links_path}\n')
    with open(links_path, 'w') as file:
        file.write("\n".join(urls))
    api.logout()

    # Download product bundles
    if args.download:

        urls_to_download = download.check_for_downloaded_scenes(urls, output_dir, no_partial_dls=True)

        # get corresponding entries from dlProductIds
        if len(urls) != len(urls_to_download):
            productIds_to_download = [
                re.search(utils.PRODUCT_ID_REGEX, x)[0] for x in urls_to_download
                if re.search(utils.PRODUCT_ID_REGEX, x)
            ]
            data_volume_to_download = sum(
                [x.get('filesize') for x in dlProductIds if x.get('displayId') in productIds_to_download]
            )
            n_left = len(urls_to_download)
            if not n_left:
                print(f'All products already present in filesystem.\n{output_dir}\nExiting.')
                exit()
            print(f'{len(urls) - len(urls_to_download)} product bundles found in filesystem, '
                  f'{n_left} left to download.\n'
                  f'Remaining download size: {utils.bytes_to_humanreadable(data_volume_to_download)}\n')
        download.download(urls_to_download, output_dir)
        print('Download complete')
        exit(0)
