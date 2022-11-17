import json
import sys

import requests

import landsatlinks.utils as utils


class eeapi(object):

    def __init__(self, user: str, password: str):
        self.endpoint = 'https://m2m.cr.usgs.gov/api/api/json/stable/'
        self.key = self.login(user, password)

    def login(self, user: str, password: str) -> str:
        loginData = json.dumps({'username': user, 'password': password, 'catalogID': 'EE'})
        with requests.post(f'{self.endpoint}login?', data=loginData).json() as response:
            if response.get('errorCode', None):
                print(f'Error: {response["errorCode"]}: {response["errorMessage"]}\n'
                      'Please check your login data.\n'
                      'Login will fail if you did not request access to the M2M API yet.\n'
                      'Request access through your user profile at https://ers.cr.usgs.gov/')
                exit(1)
            return response['data']

    def logout(self) -> None:
        self.request('logout')

    def request(self, request_code: str, **kwargs) -> dict:
        """
        Send a request to the machine2machine API.
        :type request_code: string
        :param request_code: Indicating method to API. List of codes: https://m2m.cr.usgs.gov/api/docs/reference/
        :type kwargs: dict
        :param kwargs: parameterization of the API request.
        :return: API response as dict
        """
        url = f'{self.endpoint}{request_code}'
        params = json.dumps(kwargs)
        headers = {'X-Auth-Token': self.key}
        with requests.post(url, params, headers=headers).json() as response:
            if response.get('errorCode', None):
                if response['errorCode'] == 'RATE_LIMIT_USER_DL':
                    print('Rate limit exceeded. Will sleep for 15 minutes.')
                    utils.countdown(905)
                    with requests.post(url, params, headers=headers).json() as r:
                        if r.get('errorCode', None):
                            print(f'Error: {r["errorCode"]}: {r["errorMessage"]}')
                            print('M2M API threw an error despite waiting.\n'
                                  'Please open an issue on github if the error persists.')
                            sys.exit(1)
                        return r['data']
                else:
                    print(f'Error: {response["errorCode"]}: {response["errorMessage"]}')
                    sys.exit(1)
            else:
                return response['data']

    def scene_search(self,
                     start: str, end: str,
                     dataset_name: str = None, entity_id=None,
                     seasonal_filter: list = None, pr_list: list = None,
                     max_results: int = 50000, **kwargs):
        """
        Search for scenes matching search criteria
        :param start: Temporal filter: start date
        :param end: Temporal filter: end date
        :param dataset_name: Name of the dataset to be queried (e.g. 'landsat_ot_c2_l1')
        :param entity_id: Entity ID to directly search for scenes
                          (legacy identifier in the format 'LC81920272020347LGN00')
        :param seasonal_filter: Temporal filter: months to be included (list of int)
        :param pr_list: Filter by path/row (list of int or str)
        :param max_results: maximum number of results returned
        :param kwargs: additional filters for the metadataFilter childFilters
        :return: List containing one dict per scene
        """
        if not dataset_name:
            print("No dataset defined. Use 'landsat_ot_c2_l1', 'landsat_etm_c2_l1', or 'landsat_tm_c2_l1'")
            exit(1)
        if dataset_name == 'landsat_ot_c2_l1':
            kwargs.update(sensor='OLI_TIRS', nadir='NADIR')

        if pr_list:
            paths = [pr[0:3] for pr in pr_list]
            rows = [pr[3:6] for pr in pr_list]
            p_min = min(paths)
            p_max = max(paths)
            r_min = min(rows)
            r_max = max(rows)
            kwargs.update(path_min=p_min, path_max=p_max, row_min=r_min, row_max=r_max)

        childFilters = self.create_child_filters(**kwargs)
        sceneFilter = {
            'acquisitionFilter': {'start': start, 'end': end},
            'metadataFilter': {
                'filterType': 'and',
                'childFilters': childFilters
            }
        }
        if seasonal_filter:
            sceneFilter.update(seasonalFilter=seasonal_filter)
        searchParams = {
            'datasetName': dataset_name,
            'includeUnknownCloudCover': False,
            'maxResults': max_results,
            'sceneFilter': sceneFilter
        }
        if entity_id:
            searchParams.update(entityId=entity_id)

        response = self.request('scene-search', **searchParams)
        if response.get('errorCode', None):
            print(f'Error: {response["errorCode"]}: {response["errorMessage"]}')
            sys.exit(1)
        else:
            return response['results']

    def get_download_options(self, dataset_name, scene_ids):
        """
        Retrieve download options, filter out the product bundles
        :param dataset_name: Name of the dataset to be queried (e.g., 'landsat_ot_c2_l1')
        :param scene_ids: List of entityIds (legacy scene identifiers, e.g., 'LC81920272020347LGN00')
        :return: List of dictionaries containing entity id, product id, display id, and filesize for each
                 collection 2 level-1 product bundle
        """

        sceneIdsSplit = [scene_ids[i:i + 5000] for i in range(0, len(scene_ids), 5000)]
        dlOptions = []
        for i, entity_ids in enumerate(sceneIdsSplit):
            dl_options_params = {'datasetName': dataset_name, 'entityIds': entity_ids}
            response = self.request('download-options', **dl_options_params)
            dlOptions.extend(response)

        dlProductIds = []
        for product in dlOptions:
            # Make sure the product is available for this scene
            if product['productName'] == 'Landsat Collection 2 Level-1 Product Bundle':
                if product['available'] is True:
                    dlProductIds.append(
                        {
                            'entityId': product['entityId'],
                            'productId': product['id'],
                            'displayId': product['displayId'],
                            'filesize': product['filesize']
                        }
                    )

        return dlProductIds

    def retrieve_search_results(
            self, datasetName, data_type_l1, tier,
            start, end, seasonalFilter,
            minCC, maxCC,
            prList
    ):
        """
        Combine scene_search and get_download_options, filter the results by allowed path/row, and get total size
        :return: Dictionary containing scene IDs, legacy IDs, and filesize for each scene
        """
        sceneResponse = self.scene_search(
            dataset_name=datasetName,
            pr_list=prList,
            start=start, end=end, seasonal_filter=seasonalFilter,
            min_cc=minCC, max_cc=maxCC,
            data_type_l1=data_type_l1, tier=tier
        )
        filteredSceneResponse = utils.filter_results_by_pr(sceneResponse, prList)
        if len(filteredSceneResponse) >= 15000:
            print(f'Warning: The M2M API only allows requesting 15000 scenes/15 min. '
                  f'{utils.PROG_NAME} will pause for 15 mins if rate limiting occurs.')
        legacyIds = [s.get('entityId') for s in filteredSceneResponse]
        dlProductIds = self.get_download_options(dataset_name=datasetName, scene_ids=legacyIds)

        return dlProductIds

    def get_download_links(self, dl_product_ids):
        """
        Retrieve download links for product bundles.
        Requests are split into chunks of 1000 as large numbers have been leading to issues.
        :param dl_product_ids: product ids (e.g., '5e81f14ff4f9941c') from get_download_options
        :return: List of download urls
        """

        dlSplit = [dl_product_ids[i:i + 1000] for i in range(0, len(dl_product_ids), 1000)]
        # Generate links
        urls = []
        for i, downloads in enumerate(dlSplit):
            dl_request_params = {'downloads': downloads}
            # Call the download to get the direct download urls
            response = self.request('download-request', **dl_request_params)
            for download in response['availableDownloads']:
                urls.append(download['url'])

        return urls

    @staticmethod
    def create_meta_dict(filter_id: str, filter_type: str, **kwargs) -> dict:
        meta_dict = {'filterId': filter_id, 'filterType': filter_type}
        for name, value in kwargs.items():
            meta_dict[name] = value
        return meta_dict

    def create_child_filters(self, **kwargs) -> list:
        # use .get method to get value for key in position 1, use default value in 2 if key doesn't exist in dict
        data_type_l1 = kwargs.get('data_type_l1', 'L1TP')
        tier = kwargs.get('tier', 'T1')
        day_night = kwargs.get('day_night', 'DAY')

        filters = []

        if data_type_l1:
            filters.append(
                self.create_meta_dict(
                    filter_id='5e81f14fcf660794',
                    filter_type='value',
                    value=data_type_l1
                )
            )
        if tier:
            filters.append(
                self.create_meta_dict(
                    filter_id='5e81f14fff5055a3',
                    filter_type='value',
                    value=tier
                )
            )
        if day_night:
            filters.append(
                self.create_meta_dict(
                    filter_id='5e81f14f61bda7c4',
                    filter_type='value',
                    value=day_night
                )
            )
        if any([arg in kwargs for arg in ['min_cc', 'max_cc']]):
            if kwargs['min_cc']:
                min_cc = kwargs['min_cc']
            else:
                min_cc = 0
            if kwargs['max_cc']:
                max_cc = kwargs['max_cc']
            else:
                max_cc = 100
            filters.append(
                self.create_meta_dict(
                    '5f6aa1a4e0985d4c',
                    filter_type='between',
                    firstValue=min_cc,
                    secondValue=max_cc
                )
            )
        if 'path_min' in kwargs and 'path_max' in kwargs:
            filters.append(
                self.create_meta_dict(
                    '5e81f14f8faf8048',
                    filter_type='between',
                    firstValue=kwargs['path_min'],
                    secondValue=kwargs['path_max']
                )
            )
        if 'row_min' in kwargs and 'row_max' in kwargs:
            filters.append(
                self.create_meta_dict(
                    '5e81f14f8d2a7c24',
                    filter_type='between',
                    firstValue=kwargs['row_min'],
                    secondValue=kwargs['row_max']
                )
            )
        if 'sensor' in kwargs and kwargs['sensor']:
            filters.append(
                self.create_meta_dict(
                    filter_id='5e81f14f85d499dc',
                    filter_type='value',
                    value=kwargs['sensor']
                )
            )
        if 'nadir' in kwargs and kwargs['nadir']:
            filters.append(
                self.create_meta_dict(
                    filter_id='5e81f150e42bc489',
                    filter_type='value',
                    value='NADIR'
                )
            )

        return filters
