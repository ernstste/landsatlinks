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
        print(f'No arguments provided, run "{utils.PROG_NAME} --help" for more information')
        exit(1)

    # validate output directory
    output_dir = os.path.realpath(args.output_dir)
    utils.validate_file_paths(output_dir, 'downloads', file=False, write=True)

    # validate FORCE queue file path
    queue_path = args.queue_file
    if queue_path:
        if os.path.isfile(queue_path):
            utils.validate_file_paths(queue_path, 'queue', file=True, write=True)
        else:
            queue_path_dir = os.path.dirname(queue_path)
            utils.validate_file_paths(queue_path_dir, 'queue', file=False, write=True)

    # check if user only wants to download only and go directly to download routine
    if all([arg in args for arg in ['url_file', 'output_dir']]):
        utils.check_os()
        utils.check_dependencies(['aria2c'])
        utils.validate_file_paths(args.url_file, 'url file', file=True, write=False)
        download.download_standalone(links_fp=args.url_file, output_dir=args.output_dir, queue_fp=queue_path)
        exit(0)

    # Check platform and dependencies in case the -n/--no-download flag is not set
    if args.download:
        utils.check_os()
        utils.check_dependencies(['aria2c'])

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
            datetime.strptime(date, '%Y%m%d')
        except ValueError:
            print('Error: Dates not provided in format YYYYMMDD,YYYYMMDD or date is invalid.')
            exit(1)
    start, end = [datetime.strftime(datetime.strptime(date, '%Y%m%d'), '%Y-%m-%d') for date in dates]
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

    # validate FORCE Level-2 log path
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
        print('\n')
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
        product_ids_logs = utils.find_files(search_path=log_path, search_type='log', recursive=True)
        if len(product_ids_logs) == 0:
            print(f'No FORCE logs found at {log_path}')
        else:
            dlProductIds = [productid for productid in dlProductIds if productid['displayId'] not in product_ids_logs]
            if len(dlProductIds) == 0:
                print(f'{len(product_ids_logs)} FORCE log files found, '
                      f'all product bundles from search already processed.\nExiting.')
                exit(0)
            print(
                f'{len(product_ids_logs)} FORCE log files found, '
                f'{len(dlProductIds)} products from search results not processed by FORCE yet.\n'
                f'Remaining download size: {utils.bytes_to_humanreadable(sum([s.get("filesize") for s in dlProductIds]))}'
            )

    # Check for existing product bundles in filesystem
    product_ids_filesystem = utils.find_files(search_path=output_dir, search_type='product', recursive=True)
    if product_ids_filesystem:
        dlProductIds = [productid for productid in dlProductIds if productid['displayId'] not in product_ids_filesystem]
        if len(dlProductIds) == 0:
            print(f'{len(product_ids_filesystem)} product bundles found in output directory, '
                  f'nothing left to download.\nExiting.')
            exit(0)
        else:
            print(
                f'{len(product_ids_filesystem)} product bundles found in output directory, '
                f'{len(dlProductIds)} not downloaded yet.\n'
                f'Remaining download size: {utils.bytes_to_humanreadable(sum([s.get("filesize") for s in dlProductIds]))}'
            )

    if args.no_action:
        exit(0)

    # Generate download links
    urls = api.get_download_links(dl_product_ids=dlProductIds)
    api.logout()

    # Download product bundles
    if args.download:
        download.download(urls=urls, output_dir=output_dir, force_queue_fp=queue_path)
        print('Download complete')
        exit(0)

    # or just save download urls to disk
    else:
        timeNow = datetime.now().strftime('%Y%m%dT%H%M%S')
        links_path = os.path.join(
            output_dir,
            f'urls_landsat_{args.sensor.replace(",", "_")}_{timeNow}.txt'
        )
        print(f'Writing download links to {links_path}\n')
        with open(links_path, 'w') as file:
            file.write("\n".join(urls))
