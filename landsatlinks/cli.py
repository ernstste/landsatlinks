from datetime import datetime
import json
from getpass import getpass
import os
import re
from landsatlinks.eeapi import eeapi
from landsatlinks.parseargs import parse_cli_arguments
import landsatlinks.utils as utils


def main():
    # ==================================================================================================================
    # 1. Check input and set up variables
    args = parse_cli_arguments()

    # path to search results
    searchResultsPath = os.path.realpath(args.results)
    utils.check_file_paths(searchResultsPath, 'search results')
    if not args.resume and os.path.exists(searchResultsPath):
        print(f'Error: Search results file already exists at {searchResultsPath}. '
              f'Use the --resume option if you want to use results from a previous search. '
              f'Exiting.')
        exit(1)
    if args.resume and not os.path.exists(searchResultsPath):
        print(f"Error: Search results file does not exist at {searchResultsPath}. Exiting.\n"
              f"(Did you accidentally set the --resume option?)")
        exit(1)

    # path to download links file
    if args.output:
        downloadLinksPath = os.path.realpath(args.output)
        utils.check_file_paths(downloadLinksPath, 'download links')

    # dataset name
    sat_dict = {'TM': 'landsat_tm_c2_l1', 'ETM': 'landsat_etm_c2_l1', 'OLI': 'landsat_ot_c2_l1'}
    datasetName = sat_dict[args.sensor]
    # path to pathrow list
    prListPath = os.path.realpath(args.pathrowlist)
    if not os.path.exists(prListPath):
        print('Error: PathRow list file does not exists. Check the filepath. Exiting.')
        exit(1)

    # date range
    dates = args.daterange.split(',')
    dateRe = re.compile('[0-9]{4}-[0-1][0-9]-[0-3][0-9]')
    for date in dates:
        if not dateRe.match(date):
            print('Error: Dates not provided in the format YYYY-MM-DD,YYYY-MM-DD')
            exit(1)
    start, end = dates
    # cloud cover
    if args.cloudcover:
        minCC, maxCC = args.cloudcover.split(',')
    # seasonal filter
    seasonalFilter = [int(month) for month in args.months.split(',')]
    # processing level
    data_type_l1 = args.level
    # tier
    tier = args.tier
    # make sure chosen combinations of tier and data_type_l1 make sense
    if data_type_l1 != 'L1TP' and tier == 'T1':
        print('Error: Tier 1 selected with processing level L1GT or L1GS (tier defaults to T1 if not specified).\n'
              'Choose Tier 2 (T2) or Real-Time (RT) for processing levels lower than L1TP.')
        exit(1)
    # load pathrow list
    try:
        prList = utils.load_tile_list(prListPath)
    except:
        print(f'Could not load path row list from {prListPath}')

    # path to FORCE Level-2 logs
    if args.forcelogs:
        logPath = os.path.realpath(args.forcelogs)
        if not os.access(os.path.dirname(logPath), os.R_OK):
            print('Error: Directory where FORCE log files are supposed to be stored does not exists or is not readable.'
                  ' Exiting.')
            exit(1)

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

    # First run: Create results file
    if not args.resume:
        sceneResponse = api.scene_search(
            dataset_name=datasetName,
            pr_list=prList,
            start=start, end=end, seasonal_filter=seasonalFilter,
            min_cc=minCC, max_cc=maxCC,
            data_type_l1=data_type_l1, tier=tier
        )
        filteredSceneResponse = utils.filter_results_by_pr(sceneResponse, prList)
        if len(filteredSceneResponse) >= 15000:
            print(f'Warning: The M2M API only allows requesting 15000 scenes/15 min. '
                  f'landsatlinks will pause for 15 mins if rate limiting occurs.')
        legacyIds = [s.get('entityId') for s in filteredSceneResponse]
        dlProductIds = api.get_download_options(dataset_name=datasetName, scene_ids=legacyIds)
        total_size = utils.bytes_to_humanreadable(sum([s.get('filesize') for s in dlProductIds]))
        print(
            f'Number of scenes found: {len(filteredSceneResponse)}\n'
            f'Total size: {total_size}'
        )
        print(f'Writing results to {searchResultsPath}')
        with open(searchResultsPath, 'w') as file:
            json.dump(dlProductIds, file)

# TODO remove search results file from workflow, make this routine standard, remove resume flag
    # Consecutive runs: check filesystem for existing downloads
    if args.resume:
        try:
            with open(searchResultsPath, 'r') as file:
                dlProductIds = json.load(file)
        except:
            print('Results file seems to be corrupt. Please fix or remove. Exiting')
            exit(1)

        print(f'Found {len(dlProductIds)} results from previous search at {searchResultsPath}.')
        assert isinstance(dlProductIds, list) and all(isinstance(element, dict) for element in dlProductIds),\
            f'Results file at {searchResultsPath} seems to be corrupt.\n' \
            f'Did you select the correct file from your last search?'

        # check for scenes already existing in the filesystem
        downloadedScenes = utils.find_files(
            search_path=os.path.dirname(searchResultsPath), search_type='product', recursive=True
        )
        print(f'{len(downloadedScenes)} products found in file system.')
        # only keep products if they don't exist on drive
        dlProductIds = utils.remove_duplicate_productids(dlProductIds, downloadedScenes)
        print(f'{len(dlProductIds)} products from previous search not found in filesystem.')

    # Check for FORCE Level-2 log files in the filesystem
    if args.forcelogs:
        print('\nChecking file system for FORCE Level-2 processing log files.')
        productIdsLogs = utils.find_files(
            search_path=logPath, search_type='log', recursive=True)
        print(f'{len(productIdsLogs)} FORCE log files found.')
        dlProductIds = utils.remove_duplicate_productids(dlProductIds, productIdsLogs)
        print(f'{len(dlProductIds)} products from search results not processed by FORCE yet.')

    # Generate download links and save to disk
    print(f'\nGenerating download links for {len(dlProductIds)} product bundles.')
    urls = api.get_download_links(dl_product_ids=dlProductIds)

    timeNow = datetime.now().strftime('%Y%m%dT%H%M%S')
    if not args.output:
        downloadLinksPath = os.path.join(os.path.dirname(searchResultsPath), f'urls_{datasetName}_{timeNow}.txt')

    print(f'Writing download links to {downloadLinksPath}')
    with open(downloadLinksPath, 'w') as file:
        file.write("\n".join(urls))
    api.logout()
    print('Done.')
